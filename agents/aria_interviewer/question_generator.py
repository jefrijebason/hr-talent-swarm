"""
agents/aria_interviewer/question_generator.py

Picks the next question ARIA should ask, based on:
  - Candidate's ai_profile (skills, claims, archetype, seniority)
  - Job's JD text + knowledge_base + interview_direction
  - Conversation history so far
  - Which dimensions have been covered vs still need coverage
  - The job's dimension_weights (auto from JD + HR override)

Strategy:
  1. Compute role-adaptive dimension weights from JD (cached on job).
  2. Track per-dimension question count vs. target.
  3. Pick the next under-covered dimension.
  4. Pull candidate questions from the pool, filter by relevance.
  5. Personalize the chosen question using GPT-4o-mini (cheap).
  6. For "is_meta" questions, GPT generates the dynamic content (3 options, etc).
"""

import os
import json
import random
import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import AzureOpenAI

from agents.aria_interviewer.question_pools import (
    DIMENSIONS,
    pool_for_dimension,
    pool_for_role,
    all_questions_for_archetype,
)

logger = logging.getLogger(__name__)

_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        )
    return _client


def _mini() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI") or os.getenv("MODEL_GPT4O_MINI") or "gpt-4o-mini"


# ════════════════════════════════════════════════════════════════════════
# 1. ROLE-ADAPTIVE DIMENSION WEIGHTS
# ════════════════════════════════════════════════════════════════════════

# Defaults per archetype (the matrix we agreed on).
_DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "engineer":  {"first_principles": 0.25, "ai_fluency": 0.30, "decomposition": 0.25, "taste": 0.10, "verification": 0.10},
    "pm":        {"first_principles": 0.30, "ai_fluency": 0.20, "decomposition": 0.25, "taste": 0.20, "verification": 0.05},
    "designer":  {"first_principles": 0.20, "ai_fluency": 0.20, "decomposition": 0.15, "taste": 0.35, "verification": 0.10},
    "data":      {"first_principles": 0.30, "ai_fluency": 0.25, "decomposition": 0.20, "taste": 0.05, "verification": 0.20},
    "ml":        {"first_principles": 0.25, "ai_fluency": 0.25, "decomposition": 0.25, "taste": 0.10, "verification": 0.15},
    "sales":     {"first_principles": 0.25, "ai_fluency": 0.25, "decomposition": 0.20, "taste": 0.20, "verification": 0.10},
    "marketing": {"first_principles": 0.20, "ai_fluency": 0.30, "decomposition": 0.20, "taste": 0.25, "verification": 0.05},
    "ops":       {"first_principles": 0.25, "ai_fluency": 0.25, "decomposition": 0.30, "taste": 0.10, "verification": 0.10},
    "cs":        {"first_principles": 0.20, "ai_fluency": 0.25, "decomposition": 0.25, "taste": 0.20, "verification": 0.10},
    "other":     {"first_principles": 0.25, "ai_fluency": 0.20, "decomposition": 0.25, "taste": 0.15, "verification": 0.15},
}


def compute_dimension_weights(job: Dict[str, Any], archetype: str) -> Dict[str, float]:
    """
    Determine the dimension weights for THIS specific role.

    Priority (highest first):
      1. HR's explicit override in job.dimension_weights
      2. JD-aware inference (we use defaults from archetype + small mini call)
      3. Pure archetype defaults
    """
    # 1. HR override wins
    hr_override = job.get("dimension_weights")
    if hr_override and isinstance(hr_override, dict):
        if _weights_are_valid(hr_override):
            return _normalize_weights(hr_override)

    # 2. Default from archetype (already tuned). Light JD adjustment could go here in V2.
    return dict(_DEFAULT_WEIGHTS.get(archetype, _DEFAULT_WEIGHTS["other"]))


def _weights_are_valid(w: Dict[str, Any]) -> bool:
    if not all(d in w for d in DIMENSIONS):
        return False
    try:
        s = sum(float(w[d]) for d in DIMENSIONS)
        return 0.95 <= s <= 1.05
    except (TypeError, ValueError):
        return False


def _normalize_weights(w: Dict[str, Any]) -> Dict[str, float]:
    out = {d: max(0.0, float(w.get(d, 0))) for d in DIMENSIONS}
    total = sum(out.values()) or 1.0
    return {d: v / total for d, v in out.items()}


# ════════════════════════════════════════════════════════════════════════
# 2. QUESTION PLANNING — how many questions per dimension
# ════════════════════════════════════════════════════════════════════════

def plan_question_counts(weights: Dict[str, float], total_questions: int) -> Dict[str, int]:
    """Allocate question slots across dimensions using weights, ensuring ≥1 per dim."""
    # Initial proportional allocation, rounded down
    plan = {d: max(1, int(weights[d] * total_questions)) for d in DIMENSIONS}
    # Add leftover slots to dimensions with highest fractional remainders
    leftover = total_questions - sum(plan.values())
    if leftover > 0:
        remainders = sorted(DIMENSIONS, key=lambda d: -(weights[d] * total_questions - plan[d]))
        for d in remainders[:leftover]:
            plan[d] += 1
    elif leftover < 0:
        # We over-allocated due to min=1 enforcement — trim from lowest-weight dim
        ordered = sorted(DIMENSIONS, key=lambda d: weights[d])
        idx = 0
        while leftover < 0 and idx < len(ordered):
            if plan[ordered[idx]] > 1:
                plan[ordered[idx]] -= 1
                leftover += 1
            idx += 1
    return plan


# ════════════════════════════════════════════════════════════════════════
# 3. NEXT-DIMENSION CHOICE
# ════════════════════════════════════════════════════════════════════════

def pick_next_dimension(
    plan: Dict[str, int],
    asked_counts: Dict[str, int],
    weights: Dict[str, float],
) -> Optional[str]:
    """Choose which dimension to ask next, based on coverage gap."""
    gaps = []
    for d in DIMENSIONS:
        remaining = plan.get(d, 0) - asked_counts.get(d, 0)
        if remaining > 0:
            # Prioritize biggest gap, weighted by importance
            score = remaining * (1 + weights.get(d, 0))
            gaps.append((score, d))
    if not gaps:
        return None
    gaps.sort(reverse=True)
    return gaps[0][1]


# ════════════════════════════════════════════════════════════════════════
# 4. PICK QUESTION FROM POOL + PERSONALIZE
# ════════════════════════════════════════════════════════════════════════

def pick_question_from_pool(
    dimension: str,
    archetype: str,
    asked_question_ids: List[str],
    candidate_skills: List[str],
) -> Optional[Dict[str, Any]]:
    """Pick one unused question from the pool for this dimension, biased by skill match."""
    pool = list(pool_for_dimension(dimension))
    # Add role-specific questions matching this dimension
    pool += [q for q in pool_for_role(archetype) if q.get("dimension") == dimension]

    # Filter out already-asked
    pool = [q for q in pool if _question_id(q) not in asked_question_ids]
    if not pool:
        return None

    # Lightly bias toward questions whose tags overlap with candidate skills
    skill_set = {s.lower() for s in candidate_skills}

    def relevance(q: Dict[str, Any]) -> int:
        return sum(1 for t in q.get("tags", []) if t.lower() in skill_set)

    pool.sort(key=lambda q: (-relevance(q), random.random()))
    return pool[0]


def _question_id(q: Dict[str, Any]) -> str:
    """Stable identifier for a pool question."""
    return q.get("text", "")[:60]


def personalize_question(
    question: Dict[str, Any],
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    is_opening: bool = False,
) -> str:
    """
    Adapt the pool's question text to this candidate + JD context.

    For most questions: lightly rewrite to reference the candidate's resume or company context.
    For "is_meta" questions: generate the dynamic content (3 alternative solutions, etc.)

    Cost-optimized: one short mini call, ~300 tokens out.
    """
    base = question.get("text", "")
    ai_profile = candidate.get("ai_profile", {}) or {}

    # Build context once
    name = candidate.get("name", "the candidate")
    role = job.get("title", "this role")
    skills = ", ".join(s.get("name", "") for s in ai_profile.get("skills", [])[:6])
    top_claim = (ai_profile.get("claims") or [{}])[0].get("text", "")
    kb = (job.get("knowledge_base") or "")[:400]
    direction = (job.get("interview_direction") or "")[:300]

    if question.get("is_meta"):
        # The question needs dynamic content generated (e.g. 3 design options to compare)
        system = (
            "You are ARIA, an AI interviewer. Generate the dynamic content for a meta-question. "
            "Output ONLY the question text the interviewer would say out loud — no preamble, no JSON."
        )
        user = f"""
Base question: {base}

Candidate context:
- Name: {name}
- Role: {role}
- Key skills: {skills}
- Notable claim from resume: {top_claim}

Company context:
{kb}

Generate the COMPLETE question text the interviewer would speak — including any examples,
comparisons, or scenarios needed. Keep it under 90 words.
"""
        return _mini_call(system, user, max_tokens=250)

    if is_opening:
        # Special: warm personalized opener referencing resume
        system = "You are ARIA, an AI interviewer. Write a personalized opening question. Output ONLY the question text, conversational tone, ~40 words."
        user = f"""
Candidate: {name}
Role they applied for: {role}
Resume highlight: {top_claim or skills}

Write a warm, specific opener that references something from their background.
Don't ask "tell me about yourself" — that's lazy. Anchor on something specific.
"""
        return _mini_call(system, user, max_tokens=120)

    # Standard personalization: tweak the question to reference candidate/company if natural
    system = (
        "You are ARIA, an AI interviewer. Lightly personalize the question — only if it makes the "
        "question MORE specific. Don't pad. Don't add fluff. Output ONLY the question text."
    )
    user = f"""
Question to personalize: {base}

Candidate context:
- Role they applied for: {role}
- Skills: {skills}
- Notable claim: {top_claim}

Company context: {kb or "(none provided)"}
HR's interview direction: {direction or "(none)"}

If the question is already specific and good, return it nearly unchanged.
If you can ground it in their actual background, do so (≤25 added words).
Never add filler. Never start with "Tell me about" unless it's the original.
"""
    return _mini_call(system, user, max_tokens=200)


# ════════════════════════════════════════════════════════════════════════
# 5. PROBE GENERATION (used by probe_logic when drilling deeper)
# ════════════════════════════════════════════════════════════════════════

def generate_probe(
    parent_question: str,
    candidate_answer: str,
    probe_depth: int,
    probe_hint: Optional[str] = None,
) -> str:
    """
    Generate a follow-up probe based on the candidate's last answer.

    probe_depth: 1 = first follow-up, 2 = second, 3 = third (cap).
    probe_hint: optional steering ("they were vague about scale" / "challenge their assumption").
    """
    system = (
        "You are ARIA, an aggressive but fair AI interviewer. Generate ONE follow-up question "
        "that drills deeper into the candidate's previous answer. Be specific. Cite what they "
        "just said. Don't waste their time. Output ONLY the question text, ~25 words."
    )
    depth_guidance = {
        1: "Push for specifics — numbers, names, mechanisms.",
        2: "Challenge their assumption. Why is what they said true?",
        3: "Last drill — make them defend the core claim with evidence or admit uncertainty.",
    }.get(probe_depth, "Push for specifics.")

    user = f"""
Original question: {parent_question}

Candidate's answer:
{candidate_answer[:1500]}

Probe depth: {probe_depth} of 3.
Probing strategy: {depth_guidance}
{f"Hint: {probe_hint}" if probe_hint else ""}

Generate the follow-up question.
"""
    return _mini_call(system, user, max_tokens=150)


# ════════════════════════════════════════════════════════════════════════
# 6. SCREEN-SHARE PROMPT (when ARIA asks candidate to share screen)
# ════════════════════════════════════════════════════════════════════════

def generate_screen_share_request(candidate: Dict[str, Any], project_claim: str) -> str:
    system = (
        "You are ARIA, an AI interviewer. Politely ask the candidate to share their screen and "
        "walk through a specific project they mentioned. Be warm, specific, time-boxed. Output "
        "ONLY the question text, ~30 words."
    )
    name = candidate.get("name", "")
    user = f"""
Project / claim to demo: {project_claim}
Candidate name: {name}

Generate the screen-share request — warm, specific, mention 5 minutes.
"""
    return _mini_call(system, user, max_tokens=120)


# ════════════════════════════════════════════════════════════════════════
# Closing / wrap-up
# ════════════════════════════════════════════════════════════════════════

def generate_closing(candidate: Dict[str, Any], role: str) -> str:
    return (
        f"That's all I had for you, {candidate.get('name', '')}. "
        f"Thank you for your thoughtful answers today. Your responses will be reviewed "
        f"and you'll hear back from us soon. Have a great day!"
    ).strip()


def generate_greeting(candidate: Dict[str, Any], role: str) -> str:
    name = candidate.get("name", "there")
    return (
        f"Hi {name}! I'm ARIA, your AI interviewer for the {role} role. "
        f"I'll be asking you a mix of questions about your thinking, your work, "
        f"and how you approach hard problems. Take your time with each answer, "
        f"and let's begin."
    )


# ════════════════════════════════════════════════════════════════════════
# Internal: single-call helper
# ════════════════════════════════════════════════════════════════════════

def _mini_call(system: str, user: str, max_tokens: int = 200) -> str:
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_mini(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip().strip('"')
    except Exception as e:
        logger.error(f"[ARIA] mini call failed: {e}")
        # Fallback: return the user-supplied base text if it's a personalize call,
        # else return a generic prompt the interview can keep going on.
        return user.split("Base question:")[-1].split("\n")[0].strip() or "Tell me more about your background."