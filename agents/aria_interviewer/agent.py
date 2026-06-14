"""
agents/aria_interviewer/agent.py

ARIA orchestrator — high-level state machine for an interview session.

Session state is persisted on the candidate document:
  candidate.ai_profile        : resume parse (set ONCE at upload)
  candidate.interview_session : live session state
  candidate.interview_briefing : final briefing (after completion)

Public API:
    start_interview(candidate_id, job_id)         -> {greeting, first_question, state}
    submit_answer(candidate_id, answer_text)       -> {next_question, action, ...}
    complete_interview(candidate_id)              -> {briefing, passed}
    resume_interview(candidate_id)                -> {last_question, state}
    get_interview_state(candidate_id)             -> {state}
    record_anti_cheat_flag(candidate_id, flag)    -> None
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.aria_interviewer import question_generator as qg
from agents.aria_interviewer import answer_evaluator as ae
from agents.aria_interviewer import probe_logic as pl
from agents.aria_interviewer import briefing_generator as bg
from agents.aria_interviewer.resume_analyzer import get_or_create_ai_profile
from agents.aria_interviewer.question_pools import DIMENSIONS

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────
# Cosmos helpers — imported lazily so the package can be imported even
# without a live Cosmos connection (helpful for unit testing).
# ────────────────────────────────────────────────────────────────────────
def _cosmos():
    from shared import cosmos_client as cx
    return cx


# ════════════════════════════════════════════════════════════════════════
# START
# ════════════════════════════════════════════════════════════════════════
def start_interview(candidate_id: str, job_id: str) -> Dict[str, Any]:
    """
    Initialize a new interview session.
    If candidate already has an active session, resume it instead.
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")
    job = cx.get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Resume an existing active session if present
    existing = candidate.get("interview_session")
    if existing and existing.get("status") == "active":
        logger.info(f"[ARIA] Resuming active session for {candidate_id}")
        return resume_interview(candidate_id)

    # 1. Ensure resume is parsed (cached)
    ai_profile = get_or_create_ai_profile(candidate)

    # 2. Compute role weights
    archetype = ai_profile.get("role_archetype", "other")
    weights = qg.compute_dimension_weights(job, archetype)

    # 3. Plan total questions
    total_questions = job.get("total_questions") or _seniority_to_count(ai_profile.get("seniority", "mid"))
    plan = qg.plan_question_counts(weights, total_questions)

    # 4. Build session
    session = {
        "session_id":             str(uuid.uuid4()),
        "candidate_id":           candidate_id,
        "job_id":                 job_id,
        "status":                 "active",
        "started_at":             datetime.utcnow().isoformat(),
        "last_activity_at":       datetime.utcnow().isoformat(),
        "started_epoch":          time.time(),
        "weights":                weights,
        "question_plan":          plan,
        "total_questions":        total_questions,
        "asked_counts":           {d: 0 for d in DIMENSIONS},
        "transcript":             [],
        "current_question":       None,
        "current_probe_depth":    0,
        "screen_share_done":      False,
        "anti_cheat_flags":       [],
        "pass_threshold":         job.get("pass_threshold", 70),
        "archetype":              archetype,
    }

    # 5. Greeting (text — TTS will be done client-side)
    greeting = qg.generate_greeting(candidate, job.get("title", "this role"))

    # 6. Pick the opening question
    opener = _pick_and_advance(session, candidate, job, is_opening=True)

    # 7. Persist
    candidate["interview_session"] = session
    candidate["status"] = "ai_interview_in_progress"
    cx.update_candidate(candidate_id, {
        "interview_session": session,
        "status": "ai_interview_in_progress",
        "ai_profile": candidate["ai_profile"],
    })

    cx.audit(candidate_id, "ARIA", "interview_started", {
        "job_id": job_id, "archetype": archetype,
        "total_questions": total_questions, "weights": weights,
    })

    return {
        "greeting":      greeting,
        "first_question": opener["text"],
        "question_dimension": opener["dimension"],
        "question_number": 1,
        "total_questions": total_questions,
        "session_id": session["session_id"],
    }


# ════════════════════════════════════════════════════════════════════════
# SUBMIT ANSWER (drives the conversation forward)
# ════════════════════════════════════════════════════════════════════════
def submit_answer(candidate_id: str, answer_text: str) -> Dict[str, Any]:
    """
    Process candidate's answer:
      1. Evaluate it
      2. Decide drill / next / wrap_up
      3. Generate next question (or closing)
      4. Update session state
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    session = candidate.get("interview_session")
    if not session or session.get("status") != "active":
        raise ValueError("No active interview session")

    job = cx.get_job(session["job_id"])
    current_q = session.get("current_question") or {}

    # 1. Evaluate
    related_claims = _related_claims(candidate, current_q.get("text", ""))
    evaluation = ae.evaluate_answer(
        question_text=current_q.get("text", ""),
        question_dimension=current_q.get("dimension", "first_principles"),
        candidate_answer=answer_text,
        candidate_ai_profile=candidate.get("ai_profile", {}),
        related_claims=related_claims,
        probe_depth_so_far=session["current_probe_depth"],
    )

    # 2. Record this Q&A turn in the transcript
    turn = {
        "q":           current_q.get("text", ""),
        "a":           answer_text,
        "dimension":   current_q.get("dimension"),
        "is_probe":    session["current_probe_depth"] > 0,
        "probe_depth": session["current_probe_depth"],
        "evaluation":  evaluation,
        "timestamp":   datetime.utcnow().isoformat(),
    }
    session["transcript"].append(turn)

    # 3. Decide what's next
    elapsed_min = (time.time() - session["started_epoch"]) / 60.0
    questions_asked = len([t for t in session["transcript"] if not t.get("is_probe")])

    move = pl.decide_next_move(
        answer_eval=evaluation,
        current_question=current_q.get("text", ""),
        current_answer=answer_text,
        current_probe_depth=session["current_probe_depth"],
        elapsed_minutes=elapsed_min,
        questions_asked=questions_asked,
        questions_planned=session["total_questions"],
    )

    response: Dict[str, Any] = {
        "action":   move["action"],
        "reason":   move.get("reason"),
        "evaluation_summary": {
            "dimension_score": evaluation.get("dimension_score"),
            "specificity":     evaluation.get("specificity"),
        },
    }

    if move["action"] == "probe":
        # Drill deeper — same dimension, increment depth
        session["current_probe_depth"] += 1
        probe_q = {
            "text":      move["probe_text"],
            "dimension": current_q.get("dimension"),
            "is_probe":  True,
        }
        session["current_question"] = probe_q
        response["next_question"] = probe_q["text"]
        response["question_dimension"] = probe_q["dimension"]
        response["is_probe"] = True

    elif move["action"] == "wrap_up":
        # Send the closing line; the interview completes after candidate's farewell
        session["status"] = "wrapping_up"
        closing = qg.generate_closing(candidate, job.get("title", "this role"))
        session["current_question"] = {"text": closing, "dimension": None, "is_closing": True}
        response["next_question"] = closing
        response["is_closing"] = True

    else:  # action == "next"
        # Check screen-share trigger before picking the next question
        if pl.should_request_screen_share(
            candidate=candidate, job=job,
            questions_asked=questions_asked,
            last_answer_eval=evaluation,
            screen_share_already_done=session["screen_share_done"],
        ):
            session["screen_share_done"] = True
            claim_text = _top_demoable_claim(candidate)
            ss_request = qg.generate_screen_share_request(candidate, claim_text)
            session["current_question"] = {
                "text": ss_request, "dimension": "decomposition",
                "is_screen_share_request": True,
            }
            response["next_question"] = ss_request
            response["is_screen_share_request"] = True
            response["question_dimension"] = "decomposition"
        else:
            session["current_probe_depth"] = 0
            next_q = _pick_and_advance(session, candidate, job, is_opening=False)
            if next_q is None:
                # Plan exhausted — wrap up
                session["status"] = "wrapping_up"
                closing = qg.generate_closing(candidate, job.get("title", "this role"))
                session["current_question"] = {"text": closing, "dimension": None, "is_closing": True}
                response["action"]   = "wrap_up"
                response["next_question"] = closing
                response["is_closing"]    = True
            else:
                response["next_question"]       = next_q["text"]
                response["question_dimension"]  = next_q["dimension"]
                response["is_probe"]            = False
                response["question_number"]    = questions_asked + 1

    # 4. Save
    session["last_activity_at"] = datetime.utcnow().isoformat()
    cx.update_candidate(candidate_id, {"interview_session": session})

    return response


# ════════════════════════════════════════════════════════════════════════
# COMPLETE
# ════════════════════════════════════════════════════════════════════════
def complete_interview(candidate_id: str) -> Dict[str, Any]:
    """
    Mark interview complete, generate briefing, store on candidate.
    Returns the briefing.
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    session = candidate.get("interview_session")
    if not session:
        raise ValueError("No interview session to complete")

    job = cx.get_job(session["job_id"])

    elapsed_seconds = time.time() - session.get("started_epoch", time.time())
    session["elapsed_seconds"] = int(elapsed_seconds)
    session["completed_at"]   = datetime.utcnow().isoformat()
    session["status"]         = "completed"

    # Generate briefing (single GPT-4o call)
    briefing = bg.generate_briefing(
        candidate=candidate, job=job, session=session,
        weights=session["weights"],
        pass_threshold=session.get("pass_threshold", 70),
    )

    # ── DEMO_MODE override: always mark as passed, regardless of score ──
    try:
        from shared.config import config
        if getattr(config, "DEMO_MODE", False):
            briefing["passed"] = True
            briefing["verdict"] = "PASS"
            briefing["talent_reserve_eligible"] = False
            # Boost score so it looks demo-worthy
            if briefing.get("composite_score", 0) < 70:
                briefing["composite_score"] = 78
            logger.info("[ARIA] DEMO_MODE: forced PASS regardless of actual score")
    except Exception:
        pass

    # Decide final candidate status — use LEGACY status names so dashboard recognizes them
    if briefing["passed"]:
        new_status = "ai_interview_complete"   # legacy name → dashboard maps to "AI Interview Passed"
    elif briefing.get("talent_reserve_eligible"):
        new_status = "talent_pool"             # legacy name → dashboard understands
    else:
        new_status = "rejected"                # legacy name → dashboard understands

    cx.update_candidate(candidate_id, {
        "interview_session":  session,
        "interview_briefing": briefing,
        "status":             new_status,
        "ai_interview_score": briefing.get("composite_score"),
        # Also write legacy fields so older dashboard panels keep working
        "ai_profile":         {**(candidate.get("ai_profile") or {}),
                               "human_interview_briefing": {
                                   "focus_on":            briefing.get("focus_on", []),
                                   "do_not_test_again":   briefing.get("do_not_test_again", []),
                                   "suggested_questions": briefing.get("suggested_questions", []),
                               }},
    })

    cx.audit(candidate_id, "ARIA", "interview_completed", {
        "composite_score": briefing.get("composite_score"),
        "passed": briefing.get("passed"),
        "verdict": briefing.get("verdict"),
        "new_status": new_status,
    })

    # ── If passed, trigger the existing pipeline resume so legacy flow continues ──
    if briefing.get("passed"):
        try:
            from agents.orchestrator.agent import resume_pipeline_after_interview
            import threading
            def _resume():
                try:
                    resume_pipeline_after_interview(candidate_id, briefing.get("composite_score", 75))
                except Exception as e:
                    logger.error(f"[ARIA] resume_pipeline_after_interview failed: {e}")
            threading.Thread(target=_resume, daemon=True).start()
            logger.info(f"[ARIA] Triggered pipeline resume for {candidate_id}")
        except ImportError:
            logger.warning("[ARIA] resume_pipeline_after_interview not found — interviewer must be assigned manually")

    return briefing


# ════════════════════════════════════════════════════════════════════════
# RESUME (continue after browser crash / network drop)
# ════════════════════════════════════════════════════════════════════════
def resume_interview(candidate_id: str) -> Dict[str, Any]:
    """
    Return enough state to let the frontend continue from where it left off.
    The "current_question" was the LAST thing ARIA said — frontend re-speaks it.
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")

    session = candidate.get("interview_session")
    if not session:
        raise ValueError("No interview session to resume")

    if session.get("status") not in ("active", "wrapping_up"):
        # Already completed — return briefing if available
        return {
            "status":   session.get("status"),
            "briefing": candidate.get("interview_briefing"),
            "message":  "Interview already completed",
        }

    questions_asked = len([t for t in session.get("transcript", []) if not t.get("is_probe")])
    current_q = session.get("current_question") or {}

    return {
        "status":            session.get("status"),
        "session_id":        session.get("session_id"),
        "last_question":     current_q.get("text", ""),
        "is_probe":          current_q.get("is_probe", False),
        "is_closing":        current_q.get("is_closing", False),
        "is_screen_share_request": current_q.get("is_screen_share_request", False),
        "question_dimension": current_q.get("dimension"),
        "question_number":   questions_asked + 1,
        "total_questions":   session.get("total_questions"),
    }


def get_interview_state(candidate_id: str) -> Dict[str, Any]:
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"Candidate {candidate_id} not found")
    session = candidate.get("interview_session")
    return {
        "has_session": bool(session),
        "status":      (session or {}).get("status"),
        "session_id":  (session or {}).get("session_id"),
    }


# ════════════════════════════════════════════════════════════════════════
# Anti-cheat flag recording (called by face/voice/vision endpoints)
# ════════════════════════════════════════════════════════════════════════
def record_anti_cheat_flag(candidate_id: str, flag: Dict[str, Any]) -> None:
    """
    Append an anti-cheat flag to the live session.
    flag schema: {type, severity, detail, source, timestamp?}
    """
    cx = _cosmos()
    candidate = cx.get_candidate(candidate_id)
    if not candidate:
        return
    session = candidate.get("interview_session") or {}
    if session.get("status") != "active":
        return
    flag.setdefault("timestamp", datetime.utcnow().isoformat())
    session.setdefault("anti_cheat_flags", []).append(flag)
    cx.update_candidate(candidate_id, {"interview_session": session})


# ════════════════════════════════════════════════════════════════════════
# Internals
# ════════════════════════════════════════════════════════════════════════
def _pick_and_advance(
    session: Dict[str, Any],
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    is_opening: bool,
) -> Optional[Dict[str, Any]]:
    """Pick the next question, personalize, attach to session, return it."""
    weights = session["weights"]
    asked_counts = session["asked_counts"]
    plan = session["question_plan"]

    dim = qg.pick_next_dimension(plan, asked_counts, weights)
    if dim is None:
        return None  # plan exhausted

    archetype = session.get("archetype", "other")
    asked_ids = [t.get("question_id") for t in session["transcript"] if t.get("question_id")]
    candidate_skills = [
        s.get("name", "")
        for s in (candidate.get("ai_profile") or {}).get("skills", [])
    ]

    raw_q = qg.pick_question_from_pool(dim, archetype, asked_ids, candidate_skills)
    if raw_q is None:
        # Pool exhausted for this dim — try a different dim once
        for alt_dim in DIMENSIONS:
            if alt_dim == dim:
                continue
            if plan.get(alt_dim, 0) - asked_counts.get(alt_dim, 0) > 0:
                raw_q = qg.pick_question_from_pool(alt_dim, archetype, asked_ids, candidate_skills)
                if raw_q:
                    dim = alt_dim
                    break
    if raw_q is None:
        return None

    personalized = qg.personalize_question(raw_q, candidate, job, is_opening=is_opening)
    asked_counts[dim] = asked_counts.get(dim, 0) + 1

    question_entry = {
        "text":        personalized,
        "dimension":   dim,
        "question_id": raw_q.get("text", "")[:60],
        "is_probe":    False,
    }
    session["current_question"]    = question_entry
    session["current_probe_depth"] = 0
    return question_entry


def _related_claims(candidate: Dict[str, Any], question_text: str) -> List[Dict[str, Any]]:
    """Find resume claims whose tags/keywords overlap with the question text."""
    profile = candidate.get("ai_profile") or {}
    claims  = profile.get("claims", [])
    if not claims:
        return []
    q_lower = question_text.lower()
    scored = []
    for c in claims:
        text = (c.get("text", "") + " " + c.get("verifiable_via", "")).lower()
        overlap = sum(1 for w in text.split() if len(w) > 4 and w in q_lower)
        if overlap > 0:
            scored.append((overlap, c))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scored[:5]]


def _top_demoable_claim(candidate: Dict[str, Any]) -> str:
    profile = candidate.get("ai_profile") or {}
    for c in profile.get("claims", []):
        text = c.get("text", "")
        if any(kw in text.lower() for kw in [
            "built", "designed", "shipped", "deployed", "dashboard",
            "app", "product", "platform", "website", "service",
        ]):
            return text
    return "the most challenging project from your resume"


def _seniority_to_count(seniority: str) -> int:
    # DEMO_MODE — cap to 3 questions for fast demos
    try:
        from shared.config import config
        if getattr(config, "DEMO_MODE", False):
            return 3
    except Exception:
        pass
    return {"junior": 8, "mid": 10, "senior": 11, "staff": 12, "principal": 12}.get(seniority, 10)