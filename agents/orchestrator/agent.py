from shared.cosmos_client import (
    save_candidate, get_candidate,
    update_candidate, write_audit
)
from shared.openai_client import ask_gpt4o, parse_json
from shared.service_bus import publish_human_gate
from shared.config import config
from agents.screener.agent import run_screener
from agents.evaluator.agent import run_evaluator
from agents.communicator.agent import run_communicator, send_email
from agents.interviewer.growth_report import generate_growth_report
import uuid

SCREENING_THRESHOLD = 60
HUMAN_THRESHOLD     = 70
HIRE_THRESHOLD      = 65

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


def create_candidate(name, email, phone, applied_role, expected_ctc):
    candidate_id = str(uuid.uuid4())
    candidate = {
        "id": candidate_id, "name": name, "email": email,
        "phone": phone, "applied_role": applied_role,
        "expected_ctc": expected_ctc, "status": "applied"
    }
    save_candidate(candidate)
    print(f"[ORCH] Candidate created: {candidate_id}")
    return candidate_id


def run_ai_pipeline(candidate_id, pdf_bytes, job_role, jd_text=DEFAULT_JD):
    """
    Stage 1: Resume Screening
    Stage 2: Send AI Interview link → PIPELINE PAUSES
    Pipeline resumes only when candidate completes the real interview.
    """
    print(f"\n[ORCH] ═══ AI PIPELINE START: {candidate_id} ═══")

    # ── STAGE 1: Resume Screening ────────────────────────────────
    print(f"[ORCH] Stage 1: Resume Screening")
    screen_result = run_screener(candidate_id, pdf_bytes, job_role)

    if "error" in screen_result:
        print(f"[ORCH] Screener failed")
        return {"status": "failed", "reason": "screener_error"}

    resume_score = screen_result.get("overall_score", 0)
    print(f"[ORCH] Resume score: {resume_score}/100")

    if resume_score < SCREENING_THRESHOLD:
        print(f"[ORCH] Score too low → Rejection")
        _send_rejection_with_growth(candidate_id)
        return {"status": "rejected", "reason": "low_resume_score",
                "resume_score": resume_score}

    # ── STAGE 2: Send AI Interview Link ──────────────────────────
    print(f"[ORCH] Stage 2: Sending AI Interview Link")

    _send_interview_link(candidate_id)

    update_candidate(candidate_id, {
        "status":      "ai_interview_sent",
        "resume_text": _get_resume_text(pdf_bytes),
        "jd_text_used": jd_text
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "ai_interview_sent", {"resume_score": resume_score})

    print(f"[ORCH] Pipeline paused — waiting for candidate to complete AI interview")
    print(f"[ORCH] ═══ AI PIPELINE PAUSED ═══\n")
    return {
        "status":       "ai_interview_sent",
        "resume_score": resume_score,
        "message":      "Waiting for candidate to complete AI interview"
    }


def resume_pipeline_after_interview(candidate_id, ai_score):
    """
    Called after candidate completes the REAL AI interview via ARIA.
    Resumes the pipeline: evaluate → assign technical interviewer.
    """
    print(f"\n[ORCH] ═══ PIPELINE RESUMING: {candidate_id} ═══")
    print(f"[ORCH] Real AI Interview score: {ai_score}/100")

    candidate    = get_candidate(candidate_id)
    resume_score = candidate.get("resume_score", 0)

    combined_ai = (resume_score * 0.4) + (ai_score * 0.6)
    print(f"[ORCH] Combined AI score: {combined_ai:.1f}/100")

    if combined_ai < SCREENING_THRESHOLD:
        print(f"[ORCH] Combined score too low → Rejection")
        update_candidate(candidate_id, {"status": "rejected"})
        _send_rejection_with_growth(candidate_id)
        return {"status": "rejected", "reason": "low_ai_scores",
                "combined": combined_ai}

    # Strong candidate → Route to Human Technical Interview
    print(f"[ORCH] Strong candidate → Technical Interview")

    profile  = candidate.get("ai_profile", {})
    briefing = profile.get("human_interview_briefing", {})

    job_id  = candidate.get("job_id", "")
    hr_id   = ""
    hr_name = ""

    if job_id:
        try:
            from shared.cosmos_client import get_job
            job = get_job(job_id)
            if job:
                hr_id   = job.get("posted_by_hr_id", "")
                hr_name = job.get("posted_by_hr_name", "")
                if hr_name:
                    print(f"[ORCH] Job posted by HR: {hr_name}")
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
        "combined":     combined_ai
    })

    assign_result = _assign_interviewer(
        candidate_id, job_id, hr_id, "technical"
    )
    print(f"[ORCH] Assignment: {assign_result}")

    # Notify HR who posted the JD
    _notify_hr_of_progress(candidate_id, "ai_interview_passed",
        f"AI Interview passed. Score: {ai_score}/100. Technical interview being scheduled.")

    print(f"[ORCH] ═══ PIPELINE RESUMED — TECHNICAL ASSIGNED ═══\n")
    return {
        "status":     "needs_technical_interview",
        "combined":   combined_ai,
        "assignment": assign_result
    }


def _assign_interviewer(candidate_id, job_id, hr_id, interview_type):
    try:
        from agents.interviewer_pool.agent import assign_interviewer_to_candidate
        result = assign_interviewer_to_candidate(
            candidate_id, job_id, hr_id, interview_type
        )
        print(f"[ORCH] Interviewer pool: {result.get('status')}")
        return result
    except Exception as e:
        print(f"[ORCH] Pool error: {e} — falling back to service bus")
        try:
            candidate = get_candidate(candidate_id)
            briefing  = candidate.get("human_briefing", {})
            publish_human_gate("needs-scheduling", candidate_id,
                {"interview_type": interview_type, "briefing": briefing})
            from agents.scheduler.agent import run_scheduler
            run_scheduler(candidate_id, interview_type)
        except Exception as e2:
            print(f"[ORCH] Fallback also failed: {e2}")
        return {"status": "fallback_used"}


def technical_interview_result(candidate_id, tech_score,
                                system_design_score, notes, passed):
    """
    Gate 1: Technical interviewer submits scores.
    PASS → Schedule HR Round
    FAIL → Rejection email + notify HR
    """
    print(f"\n[ORCH] ═══ TECHNICAL GATE: {candidate_id} ═══")
    print(f"[ORCH] Tech: {tech_score}/10 | Passed: {passed}")

    update_candidate(candidate_id, {
        "human_tech_score": tech_score,
        "human_system_design_score": system_design_score,
        "technical_notes": notes,
        "technical_passed": passed,
        "status": "waiting_hr_interview" if passed else "rejected"
    })

    write_audit(candidate_id, "ORCHESTRATOR", "technical_gate_decision", {
        "tech_score": tech_score, "passed": passed, "notes": notes
    })

    if not passed:
        print(f"[ORCH] Technical FAILED → Rejection")
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "technical_interview")
        return {"status": "rejected", "reason": "failed_technical"}

    print(f"[ORCH] Technical PASSED → HR Round")
    candidate = get_candidate(candidate_id)
    profile   = candidate.get("ai_profile", {})
    market    = profile.get("market_intelligence", {})

    hr_briefing = {
        "focus_on": ["Why this company", "Career goals",
                     "Salary", "Leadership", "Culture fit"],
        "market_rate":        market.get("market_rate"),
        "candidate_expected": candidate.get("expected_ctc"),
        "ai_score":           candidate.get("ai_interview_score"),
        "technical_score":    tech_score
    }

    update_candidate(candidate_id, {
        "hr_briefing": hr_briefing, "status": "waiting_hr_interview"
    })

    job_id = candidate.get("job_id", "")
    hr_id  = candidate.get("hr_id", "")

    assign_result = _assign_interviewer(
        candidate_id, job_id, hr_id, "hr_round"
    )

    _notify_hr_of_progress(candidate_id, "technical_passed",
        f"Technical passed. Score: {tech_score}/10. HR round scheduled.")

    print(f"[ORCH] ═══ TECHNICAL GATE COMPLETE ═══\n")
    return {"status": "needs_hr_interview", "hr_briefing": hr_briefing}


def hr_interview_result(candidate_id, culture_score,
                         communication_score, agreed_salary,
                         notes, hired):
    """
    Gate 2: HR submits scores.
    HIRE → Offer letter sent + notify HR
    REJECT → Rejection + growth report + notify HR
    """
    print(f"\n[ORCH] ═══ HR GATE: {candidate_id} ═══")
    print(f"[ORCH] Culture: {culture_score}/10 | Hired: {hired}")

    update_candidate(candidate_id, {
        "human_culture_score": culture_score,
        "human_communication_score": communication_score,
        "agreed_salary": agreed_salary,
        "hr_notes": notes, "status": "evaluating"
    })

    write_audit(candidate_id, "ORCHESTRATOR", "hr_gate_decision", {
        "culture_score": culture_score, "hired": hired, "notes": notes
    })

    if not hired:
        print(f"[ORCH] HR REJECTED")
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "hr_interview")
        return {"status": "rejected", "reason": "failed_hr"}

    print(f"[ORCH] HR APPROVED → Final evaluation")
    eval_result = run_evaluator(candidate_id)
    decision    = eval_result.get("decision")
    print(f"[ORCH] Final decision: {decision}")

    if decision == "HIRE":
        run_communicator(candidate_id, "HIRE")
        _send_growth_report(candidate_id, hired=True)
        _notify_hr_of_hire(candidate_id,
            eval_result.get("final_score", 0), agreed_salary)
    else:
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "final_evaluation")

    print(f"[ORCH] ═══ HR GATE COMPLETE ═══\n")
    return {"status": "complete", "decision": decision,
            "final_score": eval_result.get("final_score")}


# ── HR Notifications ──────────────────────────────────────────────

def _notify_hr_of_progress(candidate_id, stage, message):
    try:
        candidate = get_candidate(candidate_id)
        hr_id = candidate.get("hr_id", "")
        if not hr_id:
            return
        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            return
        send_email(
            to_address=hr["email"],
            subject=f"Pipeline Update: {candidate['name']}",
            body_html=f"""
<h2>Candidate Update</h2>
<p>Hi {hr['name']},</p>
<p><strong>{candidate['name']}</strong> — {candidate['applied_role']}</p>
<p>Stage: {stage.replace('_',' ').title()}</p>
<p>{message}</p>
<p>AI Score: {candidate.get('ai_interview_score','N/A')}/100</p>
<a href="http://localhost:3000" style="display:inline-block;background:#4f46e5;
color:#fff;padding:10px 20px;text-decoration:none;border-radius:8px;
font-weight:bold">View Dashboard</a>
""")
        print(f"[ORCH] HR notified: {hr['name']} — {stage}")
    except Exception as e:
        print(f"[ORCH] HR notification error: {e}")


def _notify_hr_of_rejection(candidate_id, stage):
    try:
        candidate = get_candidate(candidate_id)
        hr_id = candidate.get("hr_id", "")
        if not hr_id:
            return
        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            return
        send_email(
            to_address=hr["email"],
            subject=f"Candidate Not Proceeding: {candidate['name']}",
            body_html=f"""
<h2>Candidate Update</h2>
<p>Hi {hr['name']},</p>
<p><strong>{candidate['name']}</strong> did not proceed past {stage.replace('_',' ')}.</p>
<p>Resume: {candidate.get('resume_score','N/A')}/100 |
AI: {candidate.get('ai_interview_score','N/A')}/100</p>
<p>Growth report sent to candidate.</p>
""")
    except Exception as e:
        print(f"[ORCH] HR rejection notify error: {e}")


def _notify_hr_of_hire(candidate_id, final_score, agreed_salary):
    try:
        candidate = get_candidate(candidate_id)
        hr_id = candidate.get("hr_id", "")
        if not hr_id:
            return
        from shared.cosmos_client import get_hr_user
        hr = get_hr_user(hr_id)
        if not hr:
            return
        send_email(
            to_address=hr["email"],
            subject=f"Offer Sent: {candidate['name']}",
            body_html=f"""
<h2>Offer Sent!</h2>
<p>Hi {hr['name']},</p>
<p><strong>{candidate['name']}</strong> — {candidate['applied_role']}</p>
<p>Final Score: {final_score}/100 | Salary: {agreed_salary}</p>
<p>Candidate has 5 business days to accept.</p>
<a href="http://localhost:3000" style="display:inline-block;background:#059669;
color:#fff;padding:10px 20px;text-decoration:none;border-radius:8px;
font-weight:bold">View Dashboard</a>
""")
    except Exception as e:
        print(f"[ORCH] HR hire notify error: {e}")


# ── Helpers ───────────────────────────────────────────────────────

def _get_resume_text(pdf_bytes):
    import pdfplumber, io
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


def _send_rejection_with_growth(candidate_id):
    try:
        run_communicator(candidate_id, "REJECT")
        _send_growth_report(candidate_id, hired=False)
    except Exception as e:
        print(f"[ORCH] Rejection email error: {e}")


def _send_growth_report(candidate_id, hired):
    try:
        candidate = get_candidate(candidate_id)
        profile = candidate.get("ai_profile", {})
        if profile:
            report = generate_growth_report(candidate, profile, hired)
            print(f"[ORCH] Growth report: {report.get('subject')}")
    except Exception as e:
        print(f"[ORCH] Growth report error: {e}")


def _send_interview_link(candidate_id):
    """Send AI interview link directly to candidate email."""
    try:
        import urllib.parse
        candidate = get_candidate(candidate_id)
        if not candidate or not candidate.get("email"):
            print(f"[ORCH] No email for candidate {candidate_id}")
            return

        name = urllib.parse.quote(candidate.get("name", "Candidate"))
        role = urllib.parse.quote(candidate.get("applied_role", ""))

        interview_url = (
            f"http://localhost:3001"
            f"?interview={candidate_id}"
            f"&name={name}&role={role}&rounds=3"
        )

        send_email(
            to_address=candidate["email"],
            subject=f"AI Interview Ready — {candidate.get('applied_role', '')}",
            body_html=f"""
<h2>Congratulations, {candidate['name']}!</h2>
<p>Your resume scored well and you've been selected for
the AI interview for <strong>{candidate.get('applied_role','')}</strong>.</p>

<table style="border-collapse:collapse;width:100%;max-width:400px;margin:20px 0">
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Format</td>
    <td style="padding:10px">Text conversation with ARIA (AI)</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Rounds</td>
    <td style="padding:10px">3 rounds</td>
</tr>
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Duration</td>
    <td style="padding:10px">~8 minutes</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold;color:#d97706">Deadline</td>
    <td style="padding:10px;color:#d97706;font-weight:bold">Complete within 3 days</td>
</tr>
</table>

<p><strong>Tips:</strong></p>
<ul>
<li>Find a quiet spot with stable internet</li>
<li>Be specific with real examples from your experience</li>
<li>Take your time — thoughtful answers beat fast ones</li>
<li>You can resume once if disconnected</li>
</ul>

<a href="{interview_url}"
   style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#6366f1);
   color:#fff;padding:14px 32px;text-decoration:none;border-radius:12px;
   font-weight:bold;font-size:16px;margin:16px 0">
   Start AI Interview
</a>

<p style="color:#a8a29e;font-size:12px;margin-top:20px">
This link is unique to you. Do not share it.
Complete within 3 days to stay in the pipeline.
</p>
""")
        print(f"[ORCH] AI Interview link sent to {candidate['email']}")
    except Exception as e:
        print(f"[ORCH] Interview link error: {e}")