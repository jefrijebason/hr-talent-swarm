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

# ── Thresholds ──────────────────────────────────────────────────
SCREENING_THRESHOLD = 60
HUMAN_THRESHOLD     = 70
HIRE_THRESHOLD      = 65

# ── Default JD ──────────────────────────────────────────────────
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
    Runs entirely with AI.
    If strong enough → routes to Human Technical Interview
    using the Interviewer Pool with smart matching.
    """
    print(f"\n[ORCH] ═══ AI PIPELINE START: {candidate_id} ═══")

    # ── STAGE 1: Resume Screening ────────────────────────────────
    print(f"[ORCH] Stage 1: Resume Screening")
    screen_result = run_screener(
        candidate_id, pdf_bytes, job_role
    )

    if "error" in screen_result:
        print(f"[ORCH] Screener failed")
        return {"status": "failed", "reason": "screener_error"}

    resume_score = screen_result.get("overall_score", 0)
    print(f"[ORCH] Resume score: {resume_score}/100")

    # Below threshold → auto reject
    if resume_score < SCREENING_THRESHOLD:
        print(f"[ORCH] Score too low → Rejection")
        _send_rejection_with_growth(candidate_id)
        return {
            "status":       "rejected",
            "reason":       "low_resume_score",
            "resume_score": resume_score
        }

    # ── STAGE 2: AI Interview ────────────────────────────────────
    print(f"[ORCH] Stage 2: AI Interview")

    candidate   = get_candidate(candidate_id)
    resume_text = _get_resume_text(pdf_bytes)

    interview_result = run_ai_interview(
        candidate_id, resume_text, jd_text
    )

    ai_score = interview_result.get("score", 0)
    print(f"[ORCH] AI Interview score: {ai_score}/100")

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

    # ── STAGE 3: Route to Human Technical Interview ──────────────
    print(f"[ORCH] Strong candidate → Technical Interview")

    profile  = interview_result.get("profile", {})
    briefing = profile.get("human_interview_briefing", {})

    # Get job info to find HR who posted the JD
    candidate   = get_candidate(candidate_id)
    job_id      = candidate.get("job_id", "")
    hr_id       = ""
    hr_email    = ""
    hr_name     = ""

    if job_id:
        try:
            from shared.cosmos_client import get_job
            job      = get_job(job_id)
            hr_id    = job.get("posted_by_hr_id", "") if job else ""
            hr_email = job.get("posted_by_hr_email", "") if job else ""
            hr_name  = job.get("posted_by_hr_name", "") if job else ""
            print(f"[ORCH] Job posted by HR: {hr_name} ({hr_email})")
        except Exception as e:
            print(f"[ORCH] Could not get job HR: {e}")

    update_candidate(candidate_id, {
        "status":            "waiting_technical_interview",
        "human_briefing":    briefing,
        "combined_ai_score": combined_ai,
        "hr_id":             hr_id
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "routed_to_technical_interview", {
        "resume_score": resume_score,
        "ai_score":     ai_score,
        "combined":     combined_ai,
        "hr_id":        hr_id
    })

    # ── Use Interviewer Pool for Smart Assignment ────────────────
    assign_result = _assign_interviewer(
        candidate_id, job_id, hr_id, "technical"
    )
    print(f"[ORCH] Assignment result: {assign_result}")

    print(f"[ORCH] ═══ AI PIPELINE COMPLETE ═══\n")
    return {
        "status":          "needs_technical_interview",
        "resume_score":    resume_score,
        "ai_score":        ai_score,
        "combined":        combined_ai,
        "briefing":        briefing,
        "assignment":      assign_result
    }

def _assign_interviewer(candidate_id: str,
                         job_id: str,
                         hr_id: str,
                         interview_type: str) -> dict:
    """
    Assign best matched interviewer using pool.
    Falls back to service bus if pool unavailable.
    """
    try:
        from agents.interviewer_pool.agent import (
            assign_interviewer_to_candidate
        )
        result = assign_interviewer_to_candidate(
            candidate_id, job_id, hr_id, interview_type
        )
        print(f"[ORCH] Interviewer pool assignment: {result.get('status')}")
        return result

    except Exception as e:
        print(f"[ORCH] Pool assignment error: {e} — falling back to service bus")
        try:
            candidate = get_candidate(candidate_id)
            briefing  = candidate.get("human_briefing", {})
            publish_human_gate(
                "needs-scheduling",
                candidate_id,
                {
                    "interview_type": interview_type,
                    "briefing":       briefing
                }
            )
            # Auto schedule as fallback
            from agents.scheduler.agent import run_scheduler
            run_scheduler(candidate_id, interview_type)
        except Exception as e2:
            print(f"[ORCH] Fallback also failed: {e2}")

        return {"status": "fallback_used"}

def technical_interview_result(candidate_id: str,
                                tech_score: float,
                                system_design_score: float,
                                notes: str,
                                passed: bool) -> dict:
    """
    Gate 1: Technical Lead submits scores.
    PASS → Schedule HR Round using interviewer pool
    FAIL → Send rejection email
    Notifies the HR who posted the JD.
    """
    print(f"\n[ORCH] ═══ TECHNICAL GATE: {candidate_id} ═══")
    print(f"[ORCH] Tech: {tech_score}/10 | Design: {system_design_score}/10 | Passed: {passed}")

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
        print(f"[ORCH] Technical FAILED → Rejection email")
        _send_rejection_with_growth(candidate_id)

        # Notify HR who posted the JD
        _notify_hr_of_rejection(candidate_id, "technical_interview")

        return {
            "status": "rejected",
            "reason": "failed_technical_interview"
        }

    # Passed → Build HR briefing
    print(f"[ORCH] Technical PASSED → HR Round")
    candidate = get_candidate(candidate_id)
    profile   = candidate.get("ai_profile", {})
    market    = profile.get("market_intelligence", {})

    hr_briefing = {
        "focus_on": [
            "Why this company specifically",
            "Career motivation and goals",
            "Salary negotiation",
            "Leadership style",
            "Cultural fit"
        ],
        "market_rate":        market.get("market_rate"),
        "candidate_expected": candidate.get("expected_ctc"),
        "suggested_offer":    market.get("recommendation"),
        "retention_risk":     market.get("retention_risk"),
        "ai_score":           candidate.get("ai_interview_score"),
        "technical_score":    tech_score
    }

    update_candidate(candidate_id, {
        "hr_briefing": hr_briefing,
        "status":      "waiting_hr_interview"
    })

    # Get job and HR info
    job_id = candidate.get("job_id", "")
    hr_id  = candidate.get("hr_id", "")

    # Assign HR round interviewer using pool
    assign_result = _assign_interviewer(
        candidate_id, job_id, hr_id, "hr_round"
    )

    # Notify HR who posted the JD
    _notify_hr_of_progress(
        candidate_id,
        "technical_interview_passed",
        f"Technical interview passed. Score: {tech_score}/10. HR round scheduled."
    )

    print(f"[ORCH] ═══ TECHNICAL GATE COMPLETE ═══\n")
    return {
        "status":      "needs_hr_interview",
        "hr_briefing": hr_briefing,
        "assignment":  assign_result
    }

def hr_interview_result(candidate_id: str,
                         culture_score: float,
                         communication_score: float,
                         agreed_salary: str,
                         notes: str,
                         hired: bool) -> dict:
    """
    Gate 2: HR Manager submits scores after HR Round.
    HIRE → Offer letter sent
    REJECT → Rejection with feedback
    Notifies the HR who posted the JD either way.
    """
    print(f"\n[ORCH] ═══ HR GATE: {candidate_id} ═══")
    print(f"[ORCH] Culture: {culture_score}/10 | Hired: {hired}")

    update_candidate(candidate_id, {
        "human_culture_score":       culture_score,
        "human_communication_score": communication_score,
        "agreed_salary":             agreed_salary,
        "hr_notes":                  notes,
        "status":                    "evaluating"
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
        print(f"[ORCH] HR REJECTED → Rejection email")
        _send_rejection_with_growth(candidate_id)

        # Notify HR who posted the JD
        _notify_hr_of_rejection(candidate_id, "hr_interview")

        return {
            "status": "rejected",
            "reason": "failed_hr_interview"
        }

    # HR approved → Final evaluation
    print(f"[ORCH] HR APPROVED → Final evaluation")
    eval_result = run_evaluator(candidate_id)
    decision    = eval_result.get("decision")

    print(f"[ORCH] Final decision: {decision}")

    if decision == "HIRE":
        run_communicator(candidate_id, "HIRE")
        _send_growth_report(candidate_id, hired=True)

        # Notify HR who posted the JD — HIRED
        _notify_hr_of_hire(
            candidate_id,
            eval_result.get("final_score", 0),
            agreed_salary
        )
    else:
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "final_evaluation")

    print(f"[ORCH] ═══ HR GATE COMPLETE ═══\n")
    return {
        "status":      "complete",
        "decision":    decision,
        "final_score": eval_result.get("final_score")
    }

# ── HR Notification Functions ────────────────────────────────────

def _notify_hr_of_progress(candidate_id: str,
                             stage: str,
                             message: str):
    """
    Notify the HR who posted the JD about candidate progress.
    This ensures HR is always in the loop.
    """
    try:
        candidate = get_candidate(candidate_id)
        hr_id     = candidate.get("hr_id", "")

        if not hr_id:
            print(f"[ORCH] No HR ID found for candidate {candidate_id}")
            return

        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            print(f"[ORCH] HR user not found: {hr_id}")
            return

        from agents.communicator.agent import send_email
        send_email(
            to_address=hr["email"],
            subject=f"📊 Pipeline Update: {candidate['name']} — {candidate['applied_role']}",
            body_html=f"""
<h2>Candidate Pipeline Update</h2>
<p>Hi {hr['name']},</p>
<p>Here is an update on a candidate for the role you posted:</p>

<table style="border-collapse:collapse;width:100%;max-width:500px">
<tr style="background:#f8fafc">
    <td style="padding:10px;font-weight:bold">Candidate</td>
    <td style="padding:10px">{candidate['name']}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Role</td>
    <td style="padding:10px">{candidate['applied_role']}</td>
</tr>
<tr style="background:#f8fafc">
    <td style="padding:10px;font-weight:bold">Stage</td>
    <td style="padding:10px">{stage.replace('_', ' ').title()}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Update</td>
    <td style="padding:10px">{message}</td>
</tr>
<tr style="background:#f8fafc">
    <td style="padding:10px;font-weight:bold">AI Score</td>
    <td style="padding:10px">{candidate.get('ai_interview_score', 'N/A')}/100</td>
</tr>
</table>

<br>
<a href="http://localhost:3000"
   style="background:#6366f1;color:#fff;padding:12px 24px;
          text-decoration:none;border-radius:8px;font-weight:bold">
    View in Dashboard →
</a>

<p style="color:#94a3b8;font-size:12px;margin-top:24px">
HR Talent Intelligence Swarm — Auto notification
</p>
"""
        )
        print(f"[ORCH] HR notified: {hr['name']} — {stage}")

    except Exception as e:
        print(f"[ORCH] HR notification error: {e}")

def _notify_hr_of_rejection(candidate_id: str, stage: str):
    """Notify HR when a candidate is rejected at any stage."""
    try:
        candidate = get_candidate(candidate_id)
        hr_id     = candidate.get("hr_id", "")
        if not hr_id:
            return

        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            return

        from agents.communicator.agent import send_email
        send_email(
            to_address=hr["email"],
            subject=f"❌ Candidate Not Proceeding: {candidate['name']}",
            body_html=f"""
<h2>Candidate Update</h2>
<p>Hi {hr['name']},</p>
<p><strong>{candidate['name']}</strong> has not proceeded
further in the pipeline.</p>

<table style="border-collapse:collapse;width:100%;max-width:500px">
<tr style="background:#fef2f2">
    <td style="padding:10px;font-weight:bold">Stage</td>
    <td style="padding:10px">{stage.replace('_', ' ').title()}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Resume Score</td>
    <td style="padding:10px">{candidate.get('resume_score', 'N/A')}/100</td>
</tr>
<tr style="background:#fef2f2">
    <td style="padding:10px;font-weight:bold">AI Score</td>
    <td style="padding:10px">{candidate.get('ai_interview_score', 'N/A')}/100</td>
</tr>
</table>

<p>A personalized growth report has been sent to the candidate.</p>

<a href="http://localhost:3000"
   style="background:#6366f1;color:#fff;padding:12px 24px;
          text-decoration:none;border-radius:8px;font-weight:bold">
    View Pipeline →
</a>
"""
        )
        print(f"[ORCH] HR notified of rejection: {hr['name']}")

    except Exception as e:
        print(f"[ORCH] HR rejection notification error: {e}")

def _notify_hr_of_hire(candidate_id: str,
                        final_score: float,
                        agreed_salary: str):
    """Notify HR when a candidate is hired — the best notification."""
    try:
        candidate = get_candidate(candidate_id)
        hr_id     = candidate.get("hr_id", "")
        if not hr_id:
            return

        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            return

        from agents.communicator.agent import send_email
        send_email(
            to_address=hr["email"],
            subject=f"🎉 Offer Sent: {candidate['name']} — {candidate['applied_role']}",
            body_html=f"""
<h2>🎉 Offer Letter Sent!</h2>
<p>Hi {hr['name']},</p>
<p>Great news! An offer has been sent to
<strong>{candidate['name']}</strong>.</p>

<table style="border-collapse:collapse;width:100%;max-width:500px">
<tr style="background:#f0fdf4">
    <td style="padding:10px;font-weight:bold">Candidate</td>
    <td style="padding:10px">{candidate['name']}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Role</td>
    <td style="padding:10px">{candidate['applied_role']}</td>
</tr>
<tr style="background:#f0fdf4">
    <td style="padding:10px;font-weight:bold">Final Score</td>
    <td style="padding:10px;color:#16a34a;font-weight:bold">
        {final_score}/100
    </td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Agreed Salary</td>
    <td style="padding:10px">{agreed_salary}</td>
</tr>
<tr style="background:#f0fdf4">
    <td style="padding:10px;font-weight:bold">Resume Score</td>
    <td style="padding:10px">{candidate.get('resume_score', 'N/A')}/100</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">AI Interview</td>
    <td style="padding:10px">{candidate.get('ai_interview_score', 'N/A')}/100</td>
</tr>
</table>

<p>The candidate has 5 business days to accept the offer.
You will be notified when they respond.</p>

<a href="http://localhost:3000"
   style="background:#16a34a;color:#fff;padding:12px 24px;
          text-decoration:none;border-radius:8px;font-weight:bold">
    View in Dashboard →
</a>

<p style="color:#94a3b8;font-size:12px;margin-top:24px">
HR Talent Intelligence Swarm — Auto notification
</p>
"""
        )
        print(f"[ORCH] HR notified of hire: {hr['name']}")

    except Exception as e:
        print(f"[ORCH] HR hire notification error: {e}")

# ── Helper Functions ─────────────────────────────────────────────

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
            print(f"[ORCH] Growth report: {report.get('subject')}")
    except Exception as e:
        print(f"[ORCH] Growth report error: {e}")