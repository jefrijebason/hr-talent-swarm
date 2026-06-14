"""
agents/vibe_engineering/agent.py

Orchestrator for the Vibe Engineering Challenge.

Public API:
    start_challenge(candidate_id)              -> {problem, session_id}
    ask_ai_assistant(candidate_id, message)    -> {response}  (logs interaction)
    submit_challenge(candidate_id, code, test_results) -> {score, passed, feedback}
    get_challenge_state(candidate_id)          -> {state}
"""
import os
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from openai import AzureOpenAI

from agents.vibe_engineering.problems import pick_problem, get_problem
from agents.vibe_engineering.evaluator import evaluate_submission

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


def _gpt4o_mini() -> str:
    return (os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI") or
            os.getenv("MODEL_GPT4O_MINI") or "gpt-4o-mini")


def _cosmos():
    from shared import cosmos_client as cx
    return cx


# ════════════════════════════════════════════════════════════════════════
# START
# ════════════════════════════════════════════════════════════════════════
def start_challenge(candidate_id: str) -> Dict[str, Any]:
    """Initialize a Vibe Engineering session for the candidate."""
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    # Resume an in-progress session if any
    existing = candidate.get("vibe_session")
    if existing and existing.get("status") == "in_progress":
        logger.info(f"[VIBE] Resuming session for {candidate_id}")
        problem = get_problem(existing["problem_id"])
        return _build_start_response(problem, existing, resuming=True)

    # Pick a problem based on candidate's role archetype
    ai_profile = candidate.get("ai_profile") or {}
    archetype = ai_profile.get("role_archetype", "engineer")
    problem = pick_problem(archetype)

    session = {
        "session_id":     str(uuid.uuid4()),
        "candidate_id":   candidate_id,
        "problem_id":     problem["id"],
        "status":         "in_progress",
        "started_at":     datetime.utcnow().isoformat(),
        "started_epoch":  time.time(),
        "time_limit_minutes": problem.get("time_limit_minutes", 30),
        "ai_interactions": [],     # log of every AI assistant request/response
        "code_snapshots":  [],     # periodic snapshots of code (anti-cheat)
        "run_attempts":    0,      # how many times they ran the code
    }

    cx.update_candidate(candidate_id, {
        "vibe_session": session,
        "status": "vibe_engineering_in_progress",
    })
    cx.audit(candidate_id, "VIBE", "challenge_started", {
        "problem_id": problem["id"],
        "session_id": session["session_id"],
    })

    return _build_start_response(problem, session, resuming=False)


def _build_start_response(problem, session, resuming):
    return {
        "session_id":    session["session_id"],
        "resuming":      resuming,
        "problem": {
            "id":           problem["id"],
            "title":        problem["title"],
            "description":  problem["description"],
            "starter_code": problem["starter_code"],
            "visible_tests": problem["test_cases_visible"],
            "time_limit_minutes": problem.get("time_limit_minutes", 30),
        },
        "elapsed_seconds":  int(time.time() - session["started_epoch"]),
        "remaining_seconds": max(0, problem.get("time_limit_minutes", 30) * 60 -
                                     int(time.time() - session["started_epoch"])),
        "ai_interactions_count": len(session.get("ai_interactions", [])),
    }


# ════════════════════════════════════════════════════════════════════════
# AI ASSISTANT
# ════════════════════════════════════════════════════════════════════════
def ask_ai_assistant(candidate_id: str, user_message: str, code_context: str = "") -> Dict[str, Any]:
    """
    Candidate asks the AI assistant for help. Every interaction is logged
    and becomes part of the evaluation.
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    session = candidate.get("vibe_session")
    if not session or session.get("status") != "in_progress":
        raise ValueError("No active Vibe Engineering session")

    problem = get_problem(session["problem_id"])

    system_prompt = f"""You are an AI coding assistant inside a technical interview.
The candidate is working on this challenge:

TITLE: {problem['title']}
DESCRIPTION: {problem['description']}

You should:
- Answer their questions, explain concepts, point them at the right approach
- Suggest code when asked, but PREFER to teach rather than write the whole solution
- Be honest when their approach has issues
- DO NOT directly hand them the complete solution unless they specifically ask for it after struggling

Their current code (if provided):
```python
{code_context}
```

Be helpful but pedagogical. This is a real interview — strategic AI usage is being evaluated."""

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_gpt4o_mini(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        ai_response = resp.choices[0].message.content
    except Exception as e:
        logger.error(f"[VIBE-AI] Failed: {e}")
        ai_response = f"AI assistant unavailable right now. Try again. ({e})"

    interaction = {
        "timestamp":   datetime.utcnow().isoformat(),
        "user_message": user_message,
        "code_context": code_context[:1000] if code_context else "",   # cap
        "ai_response": ai_response,
    }
    session.setdefault("ai_interactions", []).append(interaction)
    cx.update_candidate(candidate_id, {"vibe_session": session})

    return {
        "response": ai_response,
        "interactions_count": len(session["ai_interactions"]),
    }


# ════════════════════════════════════════════════════════════════════════
# SUBMIT
# ════════════════════════════════════════════════════════════════════════
def submit_challenge(
    candidate_id: str,
    final_code: str,
    test_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Candidate submits their final code + test run results.
    GPT-4o evaluates: code quality + AI usage + bug-fix correctness + feature correctness.
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    session = candidate.get("vibe_session")
    if not session:
        raise ValueError("No Vibe Engineering session")

    problem = get_problem(session["problem_id"])
    elapsed = time.time() - session.get("started_epoch", time.time())
    session["completed_at"] = datetime.utcnow().isoformat()
    session["elapsed_seconds"] = int(elapsed)
    session["final_code"] = final_code
    session["visible_test_results"] = test_results

    # Evaluate (GPT-4o)
    evaluation = evaluate_submission(
        problem=problem,
        final_code=final_code,
        visible_test_results=test_results,
        ai_interactions=session.get("ai_interactions", []),
        elapsed_seconds=int(elapsed),
    )

    session["evaluation"] = evaluation
    session["status"] = "completed"

    # DEMO_MODE: force pass
    try:
        from shared.config import config
        if getattr(config, "DEMO_MODE", False):
            if not evaluation.get("passed"):
                logger.info("[VIBE] DEMO_MODE: forcing PASS")
                evaluation["passed"] = True
                if evaluation.get("overall_score", 0) < 60:
                    evaluation["overall_score"] = 72
                session["evaluation"] = evaluation
    except Exception:
        pass

    # Update candidate status
    if evaluation["passed"]:
        new_status = "vibe_engineering_passed"
        next_action = "send_ai_interview_link"
    else:
        new_status = "rejected"  # legacy status — dashboard understands
        next_action = "rejected_from_coding"

    cx.update_candidate(candidate_id, {
        "vibe_session": session,
        "vibe_engineering_score": evaluation.get("overall_score"),
        "vibe_engineering_evaluation": evaluation,
        "status": new_status,
    })
    cx.audit(candidate_id, "VIBE", "challenge_completed", {
        "passed": evaluation["passed"],
        "score":  evaluation.get("overall_score"),
    })

    # If passed, kick off the AI interview link
    if evaluation["passed"]:
        try:
            from agents.orchestrator.agent import resume_pipeline_after_vibe
            import threading
            def _resume():
                try:
                    resume_pipeline_after_vibe(candidate_id)
                except Exception as e:
                    logger.error(f"[VIBE] resume_pipeline_after_vibe failed: {e}")
            threading.Thread(target=_resume, daemon=True).start()
        except ImportError:
            logger.warning("[VIBE] resume_pipeline_after_vibe not available — falling back")
            try:
                from agents.orchestrator.agent import resume_pipeline_after_coding
                import threading
                threading.Thread(target=lambda: resume_pipeline_after_coding(candidate_id), daemon=True).start()
            except Exception:
                pass
    else:
        # Reject — send rejection email
        try:
            from agents.orchestrator.agent import _send_rejection_with_growth
            import threading
            threading.Thread(target=lambda: _send_rejection_with_growth(candidate_id), daemon=True).start()
        except Exception as e:
            logger.warning(f"[VIBE] rejection email failed: {e}")

    return {
        "passed":         evaluation["passed"],
        "overall_score":  evaluation.get("overall_score"),
        "feedback":       evaluation.get("feedback"),
        "rubric_scores":  evaluation.get("rubric_scores"),
        "next_action":    next_action,
    }


# ════════════════════════════════════════════════════════════════════════
# STATE
# ════════════════════════════════════════════════════════════════════════
def get_challenge_state(candidate_id: str) -> Dict[str, Any]:
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")
    session = candidate.get("vibe_session")
    if not session:
        return {"has_session": False}
    return {
        "has_session":         True,
        "status":              session.get("status"),
        "session_id":          session.get("session_id"),
        "problem_id":          session.get("problem_id"),
        "elapsed_seconds":     int(time.time() - session.get("started_epoch", time.time())),
        "ai_interactions_count": len(session.get("ai_interactions", [])),
    }


# Periodic code snapshot — frontend calls this every ~60s for anti-cheat
def save_code_snapshot(candidate_id: str, code: str) -> None:
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        return
    session = candidate.get("vibe_session")
    if not session or session.get("status") != "in_progress":
        return
    snapshots = session.get("code_snapshots", [])
    # Cap at 30 snapshots, keep newest
    if len(snapshots) >= 30:
        snapshots = snapshots[-29:]
    snapshots.append({
        "timestamp": datetime.utcnow().isoformat(),
        "code_length": len(code),
        "code_hash": hash(code) & 0xFFFFFFFF,  # for change detection
    })
    session["code_snapshots"] = snapshots
    cx.update_candidate(candidate_id, {"vibe_session": session})