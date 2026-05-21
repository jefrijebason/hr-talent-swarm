from shared.cosmos_client import (
    save_candidate, get_candidate,
    update_candidate, write_audit
)
from shared.openai_client import ask_gpt4o, parse_json
from shared.service_bus import publish_human_gate
from shared.config import config
from agents.screener.agent import run_screener
from agents.evaluator.agent import run_evaluator
from agents.communicator.agent import run_communicator
from agents.interviewer.agent import run_ai_interview
from agents.interviewer.growth_report import generate_growth_report
import uuid

# ── Thresholds ─────────────────────────────────────────────────
SCREENING_THRESHOLD = 60   # Below this → auto reject
HUMAN_THRESHOLD     = 70   # Above this → human interview
HIRE_THRESHOLD      = 65   # Evaluator hire threshold

# ── Default JD ─────────────────────────────────────────────────
DEFAULT_JD = """
Senior AI Engineer

Requirements:
- 4+ years Python experience
- Azure AI services experience
- Experience building production ML systems
- Knowledge of multi-agent AI systems
- Strong problem-solving skills
- Team leadership experience

Responsibilities:
- Design and build AI agent systems
- Deploy ML models to production
- Lead a team of 3-4 engineers

Salary: 18-24 LPA
Location: Bangalore (Hybrid)
"""

def create_candidate(name: str, email: str,
                     phone: str, applied_role: str,
                     expected_ctc: str) -> str:
    """Create a new candidate record in Cosmos DB."""
    candidate_id = str(uuid.uuid4())
    candidate = {
        "id":           candidate_id,
        "name":         name,
        "email":        email,
        "phone":        phone,
        "applied_role": applied_role,
        "expected_ctc": expected_ctc,
        "status":       "applied"
    }
    save_candidate(candidate)
    print(f"[ORCH] Candidate created: {candidate_id}")
    return candidate_id

def run_ai_pipeline(candidate_id: str,
                    pdf_bytes: bytes,
                    job_role: str,
                    jd_text: str = DEFAULT_JD) -> dict:
    """
    Stage 1 + 2: Screening + AI Interview
    Runs entirely with AI — no human involvement.
    If strong enough → routes to Human Technical Interview.
    """
    print(f"\n[ORCH] ═══ AI PIPELINE START: {candidate_id} ═══")

    # ── STAGE 1: Resume Screening ───────────────────────────────
    print(f"[ORCH] Stage 1: Resume Screening")
    screen_result = run_screener(
        candidate_id, pdf_bytes, job_role
    )

    if "error" in screen_result:
        print(f"[ORCH] Screener failed")
        return {"status": "failed", "reason": "screener_error"}

    resume_score = screen_result.get("overall_score", 0)
    print(f"[ORCH] Resume score: {resume_score}/100")

    # Below screening threshold → auto reject
    if resume_score < SCREENING_THRESHOLD:
        print(f"[ORCH] Score too low → Rejection")

        # Generate growth report before rejecting
        _send_rejection_with_growth(candidate_id)

        return {
            "status":       "rejected",
            "reason":       "low_resume_score",
            "resume_score": resume_score
        }

    # ── STAGE 2: AI Interview ───────────────────────────────────
    print(f"[ORCH] Stage 2: AI Interview")

    # Get resume text for interview
    candidate  = get_candidate(candidate_id)
    resume_text = _get_resume_text(pdf_bytes)

    interview_result = run_ai_interview(
        candidate_id, resume_text, jd_text
    )

    ai_score = interview_result.get("score", 0)
    print(f"[ORCH] AI Interview score: {ai_score}/100")

    # Calculate combined AI score
    combined_ai = (resume_score * 0.4) + (ai_score * 0.6)
    print(f"[ORCH] Combined AI score: {combined_ai:.1f}/100")

    # Below threshold → auto reject
    if combined_ai < SCREENING_THRESHOLD:
        print(f"[ORCH] Combined score too low → Rejection")
        _send_rejection_with_growth(candidate_id)
        return {
            "status":       "rejected",
            "reason":       "low_ai_scores",
            "resume_score": resume_score,
            "ai_score":     ai_score
        }

    # Strong enough → Route to Human Technical Interview
    print(f"[ORCH] Strong candidate → Technical Interview")

    # Get human briefing from AI profile
    profile  = interview_result.get("profile", {})
    briefing = profile.get("human_interview_briefing", {})

    update_candidate(candidate_id, {
        "status":            "waiting_technical_interview",
        "human_briefing":    briefing,
        "combined_ai_score": combined_ai
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "routed_to_technical_interview", {
        "resume_score": resume_score,
        "ai_score":     ai_score,
        "combined":     combined_ai
    })

    # Notify Service Bus — schedule technical interview
    publish_human_gate(
        "needs-scheduling",
        candidate_id,
        {
            "interview_type": "technical",
            "briefing":       briefing,
            "ai_score":       ai_score,
            "resume_score":   resume_score
        }
    )

    print(f"[ORCH] ═══ AI PIPELINE COMPLETE ═══\n")
    return {
        "status":       "needs_technical_interview",
        "resume_score": resume_score,
        "ai_score":     ai_score,
        "combined":     combined_ai,
        "briefing":     briefing
    }

def technical_interview_result(candidate_id: str,
                                tech_score: float,
                                system_design_score: float,
                                notes: str,
                                passed: bool) -> dict:
    """
    Gate 1: Technical Lead submits scores after Technical Interview.
    PASS → Schedule HR Round
    FAIL → Send rejection email
    """
    print(f"\n[ORCH] ═══ TECHNICAL GATE: {candidate_id} ═══")
    print(f"[ORCH] Tech: {tech_score}/10 | Design: {system_design_score}/10 | Passed: {passed}")

    # Save technical scores
    update_candidate(candidate_id, {
        "human_tech_score":          tech_score,
        "human_system_design_score": system_design_score,
        "technical_notes":           notes,
        "technical_passed":          passed,
        "status": "waiting_hr_interview" if passed else "rejected"
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "technical_gate_decision", {
        "tech_score":          tech_score,
        "system_design_score": system_design_score,
        "passed":              passed,
        "notes":               notes
    })

    if not passed:
        # Technical failed → rejection email
        print(f"[ORCH] Technical FAILED → Rejection email")
        _send_rejection_with_growth(candidate_id)
        return {
            "status":  "rejected",
            "reason":  "failed_technical_interview"
        }

    # Passed → Schedule HR Round
    print(f"[ORCH] Technical PASSED → HR Round")
    candidate = get_candidate(candidate_id)
    profile   = candidate.get("ai_profile", {})
    market    = profile.get(
        "market_intelligence", {}
    )

    # Build HR briefing
    hr_briefing = {
        "focus_on": [
            "Why this company specifically",
            "Career motivation and goals",
            "Salary negotiation",
            "Leadership style",
            "Cultural fit"
        ],
        "market_rate":         market.get("market_rate"),
        "candidate_expected":  candidate.get("expected_ctc"),
        "suggested_offer":     market.get("recommendation"),
        "retention_risk":      market.get("retention_risk"),
        "ai_score":            candidate.get("ai_interview_score"),
        "technical_score":     tech_score
    }

    update_candidate(candidate_id, {
        "hr_briefing": hr_briefing,
        "status":      "waiting_hr_interview"
    })

    # Notify Service Bus — schedule HR round
    publish_human_gate(
        "needs-scheduling",
        candidate_id,
        {
            "interview_type": "hr",
            "hr_briefing":    hr_briefing
        }
    )

    print(f"[ORCH] ═══ TECHNICAL GATE COMPLETE ═══\n")
    return {
        "status":     "needs_hr_interview",
        "hr_briefing": hr_briefing
    }

def hr_interview_result(candidate_id: str,
                         culture_score: float,
                         communication_score: float,
                         agreed_salary: str,
                         notes: str,
                         hired: bool) -> dict:
    """
    Gate 2: HR Manager submits scores after HR Round.
    HIRE → Generate and send offer letter
    REJECT → Send rejection with feedback
    """
    print(f"\n[ORCH] ═══ HR GATE: {candidate_id} ═══")
    print(f"[ORCH] Culture: {culture_score}/10 | Comm: {communication_score}/10 | Hired: {hired}")

    # Save HR scores
    update_candidate(candidate_id, {
        "human_culture_score":       culture_score,
        "human_communication_score": communication_score,
        "agreed_salary":             agreed_salary,
        "hr_notes":                  notes,
        "status": "evaluating"
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "hr_gate_decision", {
        "culture_score":       culture_score,
        "communication_score": communication_score,
        "agreed_salary":       agreed_salary,
        "hired":               hired,
        "notes":               notes
    })

    if not hired:
        # HR rejected → rejection with feedback
        print(f"[ORCH] HR REJECTED → Rejection email")
        _send_rejection_with_growth(candidate_id)
        return {
            "status": "rejected",
            "reason": "failed_hr_interview"
        }

    # HR approved → Final evaluation → Offer letter
    print(f"[ORCH] HR APPROVED → Final evaluation")

    eval_result = run_evaluator(candidate_id)
    decision    = eval_result.get("decision")

    print(f"[ORCH] Final decision: {decision}")

    if decision == "HIRE":
        run_communicator(candidate_id, "HIRE")
        _send_growth_report(candidate_id, hired=True)
    else:
        _send_rejection_with_growth(candidate_id)

    print(f"[ORCH] ═══ HR GATE COMPLETE ═══\n")
    return {
        "status":      "complete",
        "decision":    decision,
        "final_score": eval_result.get("final_score")
    }

# ── Helper Functions ────────────────────────────────────────────

def _get_resume_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF or decode as plain text."""
    import pdfplumber
    import io
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text if text.strip() else pdf_bytes.decode("utf-8")
    except Exception:
        try:
            return pdf_bytes.decode("utf-8")
        except Exception:
            return ""

def _send_rejection_with_growth(candidate_id: str):
    """Send rejection email + growth report."""
    try:
        run_communicator(candidate_id, "REJECT")
        _send_growth_report(candidate_id, hired=False)
    except Exception as e:
        print(f"[ORCH] Rejection email error: {e}")

def _send_growth_report(candidate_id: str, hired: bool):
    """Generate and send growth report."""
    try:
        candidate = get_candidate(candidate_id)
        profile   = candidate.get("ai_profile", {})
        if profile:
            report = generate_growth_report(
                candidate, profile, hired
            )
            print(f"[ORCH] Growth report generated: {report.get('subject')}")
    except Exception as e:
        print(f"[ORCH] Growth report error: {e}")