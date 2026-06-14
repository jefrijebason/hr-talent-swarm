"""
agents/aria_interviewer/answer_evaluator.py

Scores a candidate's answer along multiple axes:

  - Per-dimension score (0-100) for the question's primary dimension
  - Specificity score (was the answer concrete or vague?)
  - Claim-validation flag (did the answer match resume claims about this topic?)
  - "Needs probe?" decision (true if vague, contradictory, or shallow)

This module returns BOTH:
  1. A score that contributes to the candidate's running dimension scores
  2. A directive used by probe_logic.py to decide drill-vs-move-on

Cost-optimized: one gpt-4o-mini call per answer (~$0.005).
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

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
# Main entry
# ════════════════════════════════════════════════════════════════════════

def evaluate_answer(
    *,
    question_text: str,
    question_dimension: str,
    candidate_answer: str,
    candidate_ai_profile: Dict[str, Any],
    related_claims: List[Dict[str, Any]],
    probe_depth_so_far: int,
) -> Dict[str, Any]:
    """
    Evaluate one answer.

    Returns:
      {
        "dimension_score": int (0-100),
        "specificity":      int (0-100),
        "depth":            int (0-100),
        "originality":      int (0-100),
        "claim_validation": "supports" | "contradicts" | "no_overlap",
        "claim_notes":      "..." (only if contradicts/supports),
        "needs_probe":      bool,
        "probe_hint":       "...",   # if needs_probe is true
        "key_signals":      ["..."], # short signals for briefing
        "concerns":         ["..."], # red flags from this answer
      }
    """
    if not candidate_answer or len(candidate_answer.strip()) < 4:
        return _empty_eval("answer too short")

    claims_text = "\n".join(
        f"- {c.get('text','')} (verify via: {c.get('verifiable_via','')})"
        for c in related_claims[:5]
    ) or "(no closely related claims)"

    system_prompt = """You are an expert AI interview evaluator. Score the candidate's answer rigorously.

You will be given:
- The interview question + which dimension it tests
- The candidate's answer
- Related claims from their resume
- How many follow-up probes have already happened on this topic

Output JSON with this exact schema:
{
  "dimension_score":   <0-100 integer for the primary dimension>,
  "specificity":       <0-100, how concrete the answer was>,
  "depth":             <0-100, how deep the thinking went>,
  "originality":       <0-100, how non-memorized the answer was>,
  "claim_validation":  "supports" | "contradicts" | "no_overlap",
  "claim_notes":       "<one sentence, only if supports/contradicts>",
  "needs_probe":       true | false,
  "probe_hint":        "<short directive for the next follow-up, if needs_probe>",
  "key_signals":       ["<5-10 word signal>", ...],
  "concerns":          ["<concern>", ...]
}

SCORING RULES:
- specificity < 50 → vague (no numbers, no names, no specifics)
- depth < 50      → surface-level (one-layer reasoning)
- originality < 40 → sounds memorized / generic
- dimension_score should reflect overall quality for the tested dimension

PROBE DECISION:
- needs_probe=true if any of: specificity<50, depth<50, claim_validation=="contradicts"
- needs_probe=false if dimension_score>=75 OR probe_depth_so_far>=3 (already drilled enough)

PROBE HINT EXAMPLES:
- "They were vague about scale — push for actual numbers"
- "Resume says 5M users but they implied <1M — challenge the discrepancy"
- "They gave a textbook answer — ask what they'd do differently knowing what they know now"

Be fair but rigorous. Don't grade on charm. Substance wins.
"""

    user_prompt = f"""
QUESTION: {question_text}
DIMENSION BEING TESTED: {question_dimension}
PROBE DEPTH SO FAR: {probe_depth_so_far} of 3 max

CANDIDATE'S ANSWER:
{candidate_answer[:3000]}

RELATED RESUME CLAIMS:
{claims_text}

Evaluate now.
"""

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_mini(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=600,
        )
        result = json.loads(resp.choices[0].message.content or "{}")

        # Hard-clamp + sane defaults
        result.setdefault("dimension_score", 60)
        result.setdefault("specificity", 60)
        result.setdefault("depth", 60)
        result.setdefault("originality", 60)
        result.setdefault("claim_validation", "no_overlap")
        result.setdefault("claim_notes", "")
        result.setdefault("needs_probe", False)
        result.setdefault("probe_hint", "")
        result.setdefault("key_signals", [])
        result.setdefault("concerns", [])

        for k in ("dimension_score", "specificity", "depth", "originality"):
            v = result.get(k, 60)
            result[k] = max(0, min(100, int(v) if isinstance(v, (int, float)) else 60))

        # Override probe decision if we've exhausted probe quota
        if probe_depth_so_far >= 3:
            result["needs_probe"] = False

        return result

    except Exception as e:
        logger.error(f"[ARIA] evaluate_answer failed: {e}")
        return _empty_eval(f"eval error: {e}")


def _empty_eval(reason: str) -> Dict[str, Any]:
    return {
        "dimension_score": 50,
        "specificity":     50,
        "depth":           50,
        "originality":     50,
        "claim_validation": "no_overlap",
        "claim_notes":     "",
        "needs_probe":     False,
        "probe_hint":      "",
        "key_signals":     [],
        "concerns":        [f"Evaluation could not run: {reason}"],
        "_eval_error":     reason,
    }


# ════════════════════════════════════════════════════════════════════════
# Score aggregation across the whole interview
# ════════════════════════════════════════════════════════════════════════

def aggregate_dimension_scores(answer_evals: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Build per-dimension averages across all answered questions.

    answer_evals expected to each carry a "dimension" field (the question's primary dim)
    and a "dimension_score".
    """
    buckets: Dict[str, List[int]] = {}
    for e in answer_evals:
        dim = e.get("dimension") or e.get("question_dimension")
        score = e.get("dimension_score")
        if not dim or score is None:
            continue
        buckets.setdefault(dim, []).append(int(score))

    return {
        dim: int(round(sum(scores) / len(scores)))
        for dim, scores in buckets.items() if scores
    }


def composite_score(
    dimension_scores: Dict[str, int],
    weights: Dict[str, float],
) -> int:
    """Weighted composite for the candidate's overall AI interview score (0-100)."""
    total = 0.0
    total_weight = 0.0
    for dim, w in weights.items():
        if dim in dimension_scores:
            total += dimension_scores[dim] * w
            total_weight += w
    if total_weight == 0:
        return 0
    return int(round(total / total_weight))