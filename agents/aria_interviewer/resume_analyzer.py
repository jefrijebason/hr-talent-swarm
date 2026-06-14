"""
agents/aria_interviewer/resume_analyzer.py

Parses a candidate's resume ONCE (at upload time) and extracts:
  - skills              : structured skill list with proficiency hints
  - claims              : verifiable statements ARIA will probe later
  - seniority           : junior | mid | senior | staff | principal
  - experience_years    : numeric
  - red_flags           : surface-level resume red flags (job hopping, gaps)
  - role_archetype      : engineer | pm | designer | data | ml | sales | marketing | ops | cs

The result is cached on the candidate document as `ai_profile`. During the
interview, ARIA reads from this cache — never re-parses.
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────
# Azure OpenAI client (uses gpt-4o-mini for cheap parsing)
# ────────────────────────────────────────────────────────────────────────
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


def _mini_model() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI") or os.getenv("MODEL_GPT4O_MINI") or "gpt-4o-mini"


# ────────────────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────────────────
def analyze_resume(resume_text: str) -> Dict[str, Any]:
    """
    Extract structured profile from a raw resume.

    Returns dict with keys:
        skills, claims, seniority, experience_years,
        red_flags, role_archetype, parsed_at
    """
    if not resume_text or len(resume_text.strip()) < 50:
        return _empty_profile("resume_text too short")

    system_prompt = """You are a resume parser. Extract structured information from the resume.

Return JSON with this schema:
{
  "skills": [{"name": "Python", "level": "expert|advanced|intermediate|beginner", "years": 3}],
  "claims": [
    {
      "text": "Led migration of 5M user database to PostgreSQL",
      "context": "TechCorp 2023",
      "verifiable_via": "ask about migration challenges, data volume, rollback strategy",
      "criticality": "high|medium|low"
    }
  ],
  "seniority": "junior|mid|senior|staff|principal",
  "experience_years": 5,
  "red_flags": ["3 jobs in past 12 months", "skill list very long without depth"],
  "role_archetype": "engineer|pm|designer|data|ml|sales|marketing|ops|cs|other"
}

RULES:
- Only flag genuinely "verifiable" claims — quantified achievements, named projects, specific tech.
- Don't flag generic statements like "worked on backend systems".
- Cap claims at 10 most important.
- Cap skills at 15 most relevant.
- Red flags should be objective (dates, list size) not subjective.
- For role_archetype, pick the BEST fit for their most recent role.
"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=_mini_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse this resume:\n\n{resume_text[:8000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content
        profile = json.loads(raw)
        profile["parsed_at"] = datetime.utcnow().isoformat()
        profile["parser_version"] = "1.0"

        # Sanity-check structure
        profile.setdefault("skills", [])
        profile.setdefault("claims", [])
        profile.setdefault("red_flags", [])
        profile.setdefault("seniority", "mid")
        profile.setdefault("experience_years", 0)
        profile.setdefault("role_archetype", "other")

        logger.info(
            f"[ARIA] Resume parsed — {len(profile['skills'])} skills, "
            f"{len(profile['claims'])} claims, archetype={profile['role_archetype']}, "
            f"seniority={profile['seniority']}"
        )
        return profile

    except Exception as e:
        logger.error(f"[ARIA] Resume parse failed: {e}", exc_info=True)
        return _empty_profile(f"parse error: {e}")


def _empty_profile(reason: str) -> Dict[str, Any]:
    return {
        "skills": [],
        "claims": [],
        "seniority": "mid",
        "experience_years": 0,
        "red_flags": [],
        "role_archetype": "other",
        "parsed_at": datetime.utcnow().isoformat(),
        "parser_version": "1.0",
        "parse_error": reason,
    }


# ────────────────────────────────────────────────────────────────────────
# Cache-aware lookup
# ────────────────────────────────────────────────────────────────────────
def get_or_create_ai_profile(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    If candidate already has ai_profile, return it.
    Otherwise parse resume_text and cache the result on the candidate.

    The CALLER is responsible for persisting the updated candidate doc back to Cosmos.
    This function only mutates the dict and returns the profile.
    """
    existing = candidate.get("ai_profile")
    if existing and "parsed_at" in existing:
        return existing

    resume_text = (
        candidate.get("resume_text")
        or candidate.get("parsed_resume_text")
        or candidate.get("resume_content")
        or ""
    )
    profile = analyze_resume(resume_text)
    candidate["ai_profile"] = profile
    return profile


# ────────────────────────────────────────────────────────────────────────
# Helpers for downstream consumers
# ────────────────────────────────────────────────────────────────────────
def top_claims_for_probing(profile: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Return the most-important resume claims worth verifying."""
    claims = profile.get("claims", [])
    high = [c for c in claims if c.get("criticality") == "high"]
    if len(high) >= limit:
        return high[:limit]
    med = [c for c in claims if c.get("criticality") == "medium"]
    return (high + med)[:limit]


def primary_skills_for_role(profile: Dict[str, Any], jd_required_skills: List[str]) -> List[str]:
    """Intersect candidate's skills with the JD's required skills."""
    candidate_skill_names = {s.get("name", "").lower() for s in profile.get("skills", [])}
    return [s for s in jd_required_skills if s.lower() in candidate_skill_names]


def seniority_to_question_count(seniority: str) -> int:
    """Map seniority → how many questions to ask."""
    return {
        "junior": 8,
        "mid": 10,
        "senior": 11,
        "staff": 12,
        "principal": 12,
    }.get(seniority, 10)