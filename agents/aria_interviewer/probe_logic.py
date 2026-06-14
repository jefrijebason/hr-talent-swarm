"""
agents/aria_interviewer/probe_logic.py

Decides whether ARIA should:
  - DRILL DEEPER on the current topic (ask a follow-up probe), or
  - MOVE ON to the next planned question

Inputs:
  - The evaluator's verdict on the latest answer (needs_probe, probe_hint, scores)
  - Current probe depth on this topic (0-3 max)
  - Time elapsed (force wrap-up after 13 min of total interview)
  - Question plan progress

Returns a directive the orchestrator can act on:
  {"action": "probe"|"next"|"wrap_up",
   "probe_text": "...",       # if action==probe
   "reason": "..."}            # for logging
"""

import logging
from typing import Any, Dict, Optional

from agents.aria_interviewer.question_generator import generate_probe

logger = logging.getLogger(__name__)

# Cap probe depth + duration lower in DEMO_MODE to keep interview short
try:
    from shared.config import config
    _DEMO = getattr(config, "DEMO_MODE", False)
except Exception:
    _DEMO = False

# Hard caps
MAX_PROBE_DEPTH      = 1 if _DEMO else 3       # demo: max 1 probe per topic
SOFT_WRAP_UP_MINUTES = 3 if _DEMO else 13      # demo: wrap up after 3 min
HARD_END_MINUTES     = 5 if _DEMO else 15      # demo: force end at 5 min


def decide_next_move(
    *,
    answer_eval: Dict[str, Any],
    current_question: str,
    current_answer: str,
    current_probe_depth: int,
    elapsed_minutes: float,
    questions_asked: int,
    questions_planned: int,
) -> Dict[str, Any]:
    """
    Returns a directive: probe / next / wrap_up.
    """
    # 1. Hard time cap → wrap up regardless
    if elapsed_minutes >= HARD_END_MINUTES:
        return {
            "action": "wrap_up",
            "reason": f"Hard time cap reached ({HARD_END_MINUTES} min)",
        }

    # 2. Approaching soft cap with most questions answered → wrap up gracefully
    if elapsed_minutes >= SOFT_WRAP_UP_MINUTES and questions_asked >= questions_planned * 0.7:
        return {
            "action": "wrap_up",
            "reason": f"Soft cap + {int(questions_asked/questions_planned*100)}% questions answered",
        }

    # 3. Probe-depth exhausted → must move on
    if current_probe_depth >= MAX_PROBE_DEPTH:
        return {
            "action": "next",
            "reason": f"Probe depth cap ({MAX_PROBE_DEPTH}) reached on this topic",
        }

    # 4. Strong, specific answer → no need to probe → move on
    score = answer_eval.get("dimension_score", 60)
    needs_probe = bool(answer_eval.get("needs_probe", False))

    if score >= 80 and not needs_probe:
        return {
            "action": "next",
            "reason": f"Strong answer (score={score}), no probe needed",
        }

    # 5. Evaluator says probe → generate probe text
    if needs_probe:
        try:
            probe_text = generate_probe(
                parent_question=current_question,
                candidate_answer=current_answer,
                probe_depth=current_probe_depth + 1,
                probe_hint=answer_eval.get("probe_hint"),
            )
        except Exception as e:
            logger.error(f"[ARIA] probe generation failed: {e}")
            probe_text = "Can you give me a more specific example of that?"

        return {
            "action": "probe",
            "probe_text": probe_text,
            "reason": f"Drill (depth={current_probe_depth+1}, score={score}, hint={answer_eval.get('probe_hint','')[:60]})",
        }

    # 6. Default → move on
    return {
        "action": "next",
        "reason": f"Default move-on (score={score})",
    }


def should_request_screen_share(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    questions_asked: int,
    last_answer_eval: Dict[str, Any],
    screen_share_already_done: bool,
) -> bool:
    """
    Smart trigger for screen-share:
      - Only if candidate has demonstrable projects
      - Only mid-interview (questions 5-8 range)
      - Skip if already done
      - More likely if last answer was vague about a project claim
    """
    if screen_share_already_done:
        return False

    if questions_asked < 4 or questions_asked > 8:
        return False

    ai_profile = candidate.get("ai_profile", {}) or {}
    claims = ai_profile.get("claims", [])
    demoable_claims = [
        c for c in claims
        if any(kw in c.get("text", "").lower()
               for kw in ["built", "designed", "shipped", "deployed", "dashboard",
                          "app", "product", "platform", "website", "service"])
    ]
    if not demoable_claims:
        return False

    # If last answer was vague about a claim, this is the perfect moment
    spec = last_answer_eval.get("specificity", 100)
    if spec < 60:
        return True

    # Otherwise trigger if we're past question 6 and haven't yet
    return questions_asked >= 6