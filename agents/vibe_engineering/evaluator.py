"""
agents/vibe_engineering/evaluator.py

GPT-4o evaluator for Vibe Engineering Challenge submissions.

Evaluates:
  1. Bug fixed correctly
  2. Feature implemented correctly
  3. Code quality (readability, idiom, naming)
  4. AI usage quality (strategic vs blind copy-paste)
  5. Verification discipline (did they test, verify AI output)
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional

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


def _gpt4o() -> str:
    return (os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O") or
            os.getenv("MODEL_GPT4O") or "gpt-4o")


def evaluate_submission(
    *,
    problem: Dict[str, Any],
    final_code: str,
    visible_test_results: List[Dict[str, Any]],
    ai_interactions: List[Dict[str, Any]],
    elapsed_seconds: int,
) -> Dict[str, Any]:
    """
    Run a single GPT-4o call to evaluate the submission.

    Returns:
      {
        "overall_score": int (0-100),
        "passed": bool,
        "rubric_scores": {rubric_key: {"score": int, "reasoning": str}},
        "feedback": str (paragraph for the candidate / HR),
        "ai_usage_analysis": str,
        "concerns": [str],
        "strengths": [str],
      }
    """
    rubric = problem.get("evaluation_rubric", {})

    # Build a transcript of AI interactions (last 10 to cap cost)
    interaction_log = []
    for i, intr in enumerate(ai_interactions[-10:]):
        interaction_log.append(
            f"Turn {i+1}:\n  Candidate asked: {intr.get('user_message','')[:300]}\n"
            f"  AI replied: {intr.get('ai_response','')[:300]}"
        )
    interaction_text = "\n\n".join(interaction_log) or "(No AI assistance used)"

    # Build test pass/fail summary
    test_summary = []
    for t in visible_test_results:
        status = "✓ PASS" if t.get("passed") else "✗ FAIL"
        test_summary.append(f"{status}: {t.get('name', '?')}")
    test_summary_text = "\n".join(test_summary) or "(No tests run)"

    system = f"""You are evaluating a candidate's submission for the Vibe Engineering Challenge.

This is NOT a LeetCode test. The candidate had access to an AI assistant. We evaluate:
1. Did they FIX the bug correctly?
2. Did they ADD the feature correctly?
3. Code quality (clean, idiomatic, well-named)
4. AI USAGE QUALITY — did they prompt strategically, verify outputs, push back on bad suggestions?
   Or did they blindly copy-paste?
5. Verification discipline — did they test their work? Did they question AI suggestions?

A candidate who used AI heavily but PRODUCED A WORKING, CLEAN SOLUTION with thoughtful prompts
should score HIGH. A candidate who avoided AI but produced buggy code should score LOWER than
that. The era of "AI helps you ship faster" is being evaluated.

A candidate who blind-pasted AI suggestions without verifying = RED FLAG.

Respond in this exact JSON schema:
{{
  "overall_score": <int 0-100>,
  "passed": <bool — true if overall_score >= 60>,
  "rubric_scores": {{
    "bug_fixed":               {{"score": <0-100>, "reasoning": "<one sentence>"}},
    "feature_works":           {{"score": <0-100>, "reasoning": "<one sentence>"}},
    "code_quality":            {{"score": <0-100>, "reasoning": "<one sentence>"}},
    "ai_usage_quality":        {{"score": <0-100>, "reasoning": "<one sentence>"}},
    "verification_discipline": {{"score": <0-100>, "reasoning": "<one sentence>"}}
  }},
  "strengths":         ["<bullet>", "<bullet>"],
  "concerns":          ["<bullet>", "<bullet>"],
  "ai_usage_analysis": "<one paragraph on HOW they used AI>",
  "feedback":          "<one paragraph for HR — recommendation summary>"
}}"""

    user = f"""## Problem
{problem.get('title')}
{problem.get('description')}

## Reference bug
{problem.get('bug_hint', '(none documented)')}

## Reference feature approach
{problem.get('feature_hint', '(none documented)')}

## Candidate's final code
```python
{final_code}
```

## Visible test results
{test_summary_text}

## AI assistant interactions ({len(ai_interactions)} total, showing last 10)
{interaction_text}

## Time taken
{elapsed_seconds // 60} minutes {elapsed_seconds % 60} seconds

Evaluate now. Respond ONLY in JSON.
"""

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_gpt4o(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500,
        )
        result = json.loads(resp.choices[0].message.content or "{}")

        # Ensure shape is good
        result.setdefault("overall_score", 50)
        result.setdefault("passed", result.get("overall_score", 50) >= 60)
        result.setdefault("rubric_scores", {})
        result.setdefault("strengths", [])
        result.setdefault("concerns", [])
        result.setdefault("ai_usage_analysis", "")
        result.setdefault("feedback", "")

        return result

    except Exception as e:
        logger.error(f"[VIBE-Eval] failed: {e}", exc_info=True)
        # Fallback — pass test result count
        passed_count = sum(1 for t in visible_test_results if t.get("passed"))
        total = max(1, len(visible_test_results))
        score = int((passed_count / total) * 70)
        return {
            "overall_score": score,
            "passed": score >= 60,
            "rubric_scores": {},
            "strengths": [],
            "concerns": [f"Evaluator error: {e}"],
            "ai_usage_analysis": "Evaluation unavailable",
            "feedback": f"Auto-graded based on {passed_count}/{total} visible tests passing.",
        }
