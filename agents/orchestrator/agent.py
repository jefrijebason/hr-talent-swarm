from shared.cosmos_client import (
    save_candidate, get_candidate,
    update_candidate, write_audit, get_job
)
from shared.openai_client import ask_gpt4o, parse_json
from shared.service_bus import publish_human_gate
from shared.config import config
from shared.agent_feed import log_agent
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
    log_agent("ORCHESTRATOR", "candidate_created", f"{name} applied for {applied_role}", candidate_id)
    return candidate_id


def run_ai_pipeline(candidate_id, pdf_bytes, job_role, jd_text=DEFAULT_JD):
    print(f"\n[ORCH] ═══ AI PIPELINE START: {candidate_id} ═══")
    log_agent("ORCHESTRATOR", "pipeline_started", f"Processing candidate for {job_role}", candidate_id)

    # ── STAGE 1: Resume Screening ────────────────────────────────
    print(f"[ORCH] Stage 1: Resume Screening")
    log_agent("ORCHESTRATOR", "screening_started", "Analyzing resume with AI", candidate_id)

    screen_result = run_screener(candidate_id, pdf_bytes, job_role)

    if "error" in screen_result:
        print(f"[ORCH] Screener failed")
        log_agent("ORCHESTRATOR", "screening_failed", "Resume analysis error", candidate_id)
        return {"status": "failed", "reason": "screener_error"}

    resume_score = screen_result.get("overall_score", 0)
    print(f"[ORCH] Resume score: {resume_score}/100")
    log_agent("ORCHESTRATOR", "screening_complete", f"Resume score: {resume_score}/100", candidate_id)

    if resume_score < SCREENING_THRESHOLD:
        print(f"[ORCH] Score too low → Rejection")
        log_agent("ORCHESTRATOR", "rejected", f"Resume score {resume_score} below threshold {SCREENING_THRESHOLD}", candidate_id)
        _send_rejection_with_growth(candidate_id)
        return {"status": "rejected", "reason": "low_resume_score",
                "resume_score": resume_score}

    # ── STAGE 2: Send AI Interview Link ──────────────────────────
    print(f"[ORCH] Stage 2: Sending AI Interview Link")

    _send_interview_link(candidate_id)
    log_agent("ORCHESTRATOR", "ai_interview_sent", "Interview link emailed to candidate", candidate_id)

    update_candidate(candidate_id, {
        "status":      "ai_interview_sent",
        "resume_text": _get_resume_text(pdf_bytes),
        "jd_text_used": jd_text
    })

    write_audit(candidate_id, "ORCHESTRATOR",
                "ai_interview_sent", {"resume_score": resume_score})

    print(f"[ORCH] Pipeline paused — waiting for candidate to complete AI interview")
    log_agent("ORCHESTRATOR", "pipeline_paused", "Waiting for AI interview completion", candidate_id)
    print(f"[ORCH] ═══ AI PIPELINE PAUSED ═══\n")
    return {
        "status":       "ai_interview_sent",
        "resume_score": resume_score,
        "message":      "Waiting for candidate to complete AI interview"
    }


def resume_pipeline_after_interview(candidate_id, ai_score):
    print(f"\n[ORCH] ═══ PIPELINE RESUMING: {candidate_id} ═══")
    print(f"[ORCH] Real AI Interview score: {ai_score}/100")
    log_agent("ORCHESTRATOR", "pipeline_resumed", f"AI Interview score: {ai_score}/100", candidate_id)

    candidate    = get_candidate(candidate_id)
    resume_score = candidate.get("resume_score", 0)

    combined_ai = (resume_score * 0.4) + (ai_score * 0.6)
    print(f"[ORCH] Combined AI score: {combined_ai:.1f}/100")
    log_agent("ORCHESTRATOR", "scores_combined", f"Combined: {combined_ai:.1f}/100 (Resume: {resume_score}, AI: {ai_score})", candidate_id)

    if combined_ai < SCREENING_THRESHOLD:
        print(f"[ORCH] Combined score too low → Rejection")
        log_agent("ORCHESTRATOR", "rejected", f"Combined {combined_ai:.1f} below threshold", candidate_id)
        update_candidate(candidate_id, {"status": "rejected"})
        _send_rejection_with_growth(candidate_id)
        return {"status": "rejected", "reason": "low_ai_scores",
                "combined": combined_ai}

    print(f"[ORCH] Strong candidate → Next stage")
    log_agent("ORCHESTRATOR", "candidate_passed", f"Combined score {combined_ai:.1f} — routing to next stage", candidate_id)

    profile  = candidate.get("ai_profile", {})
    briefing = profile.get("human_interview_briefing", {})

    job_id  = candidate.get("job_id", "")
    hr_id   = ""
    hr_name = ""

    if job_id:
        try:
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

    # Check if coding round is enabled
    job = None
    if job_id:
        job = get_job(job_id)

    if job and job.get("coding_round_enabled"):
        print(f"[ORCH] Coding round enabled — sending assessment")
        log_agent("ORCHESTRATOR", "coding_required", "Job requires coding assessment", candidate_id)

        _send_coding_assessment_link(candidate_id, job_id)
        log_agent("ORCHESTRATOR", "coding_sent", "Coding assessment link emailed", candidate_id)

        update_candidate(candidate_id, {"status": "coding_sent"})

        write_audit(candidate_id, "ORCHESTRATOR",
                    "coding_sent", {"job_id": job_id, "combined_ai_score": combined_ai})

        _notify_hr_of_progress(candidate_id, "coding_assessment_sent",
            f"Candidate passed AI interview. Coding assessment sent. Score: {ai_score}/100.")

        log_agent("ORCHESTRATOR", "pipeline_paused", "Waiting for coding assessment", candidate_id)
        print(f"[ORCH] ═══ PIPELINE PAUSED — CODING SENT ═══\n")
        return {
            "status":        "coding_sent",
            "combined":      combined_ai,
            "coding_needed": True
        }

    # No coding → go straight to technical interview
    log_agent("ORCHESTRATOR", "assigning_interviewer", "Matching best interviewer", candidate_id)

    assign_result = _assign_interviewer(
        candidate_id, job_id, hr_id, "technical"
    )
    print(f"[ORCH] Assignment: {assign_result}")
    log_agent("ORCHESTRATOR", "technical_assigned", f"Interviewer assigned: {assign_result.get('primary', 'N/A')}", candidate_id)

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
        log_agent("INTERVIEWER_POOL", "matched", f"Best match: {result.get('primary', 'N/A')}", candidate_id)
        return result
    except Exception as e:
        print(f"[ORCH] Pool error: {e} — falling back to service bus")
        log_agent("ORCHESTRATOR", "pool_fallback", f"Using scheduler fallback: {str(e)[:50]}", candidate_id)
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
    print(f"\n[ORCH] ═══ TECHNICAL GATE: {candidate_id} ═══")
    print(f"[ORCH] Tech: {tech_score}/10 | Passed: {passed}")
    log_agent("ORCHESTRATOR", "technical_feedback", f"Score: {tech_score}/10 | {'PASSED' if passed else 'FAILED'}", candidate_id)

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
        log_agent("ORCHESTRATOR", "rejected", "Failed technical interview", candidate_id)
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "technical_interview")
        return {"status": "rejected", "reason": "failed_technical"}

    print(f"[ORCH] Technical PASSED → HR Round")
    log_agent("ORCHESTRATOR", "technical_passed", f"Score: {tech_score}/10 — routing to HR round", candidate_id)

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
    print(f"\n[ORCH] ═══ HR GATE: {candidate_id} ═══")
    print(f"[ORCH] Culture: {culture_score}/10 | Hired: {hired}")
    log_agent("ORCHESTRATOR", "hr_feedback", f"Culture: {culture_score}/10 | {'HIRED' if hired else 'REJECTED'}", candidate_id)

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
        log_agent("ORCHESTRATOR", "rejected", "HR did not approve", candidate_id)
        _send_rejection_with_growth(candidate_id)
        _notify_hr_of_rejection(candidate_id, "hr_interview")
        return {"status": "rejected", "reason": "failed_hr"}

    print(f"[ORCH] HR APPROVED → Final evaluation")
    log_agent("EVALUATOR", "evaluating", "Running final weighted evaluation", candidate_id)

    eval_result = run_evaluator(candidate_id)
    decision    = eval_result.get("decision")
    print(f"[ORCH] Final decision: {decision}")
    log_agent("EVALUATOR", "decision", f"Final: {decision} | Score: {eval_result.get('final_score', 'N/A')}/100", candidate_id)

    if decision == "HIRE":
        log_agent("COMMUNICATOR", "offer_sent", "Sending offer letter to candidate", candidate_id)
        run_communicator(candidate_id, "HIRE")
        _send_growth_report(candidate_id, hired=True)
        _notify_hr_of_hire(candidate_id,
            eval_result.get("final_score", 0), agreed_salary)
        log_agent("ORCHESTRATOR", "hired", f"Candidate hired! Final score: {eval_result.get('final_score')}/100", candidate_id)
    else:
        log_agent("COMMUNICATOR", "rejection_sent", "Sending rejection + growth report", candidate_id)
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
        log_agent("COMMUNICATOR", "hr_notified", f"HR {hr['name']} notified: {stage}", candidate_id)
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
        log_agent("COMMUNICATOR", "rejection_email", "Sending rejection + growth report", candidate_id)
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
            log_agent("COMMUNICATOR", "growth_report", f"Growth report generated", candidate_id)
    except Exception as e:
        print(f"[ORCH] Growth report error: {e}")


def _send_interview_link(candidate_id):
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
        log_agent("COMMUNICATOR", "email_sent", f"AI Interview link → {candidate['email']}", candidate_id)
    except Exception as e:
        print(f"[ORCH] Interview link error: {e}")


def _send_coding_assessment_link(candidate_id, job_id=None):
    try:
        import urllib.parse
        candidate = get_candidate(candidate_id)
        if not candidate or not candidate.get("email"):
            print(f"[ORCH] No email for candidate {candidate_id}")
            return

        job_param = urllib.parse.quote(job_id or "")
        name = urllib.parse.quote(candidate.get("name", "Candidate"))
        role = urllib.parse.quote(candidate.get("applied_role", ""))

        coding_url = (
            f"http://localhost:3002"
            f"?candidate={candidate_id}"
            f"&job={job_param}"
            f"&name={name}&role={role}"
        )

        send_email(
            to_address=candidate["email"],
            subject=f"Coding Assessment Ready — {candidate.get('applied_role', '')}",
            body_html=f"""
<h2>Hello {candidate['name']},</h2>
<p>Your AI interview was successful and you're now invited to complete
the coding assessment for <strong>{candidate.get('applied_role','')}</strong>.</p>
<p>Complete the assessment within 3 days to stay in the process.</p>
<p><strong>What to expect:</strong></p>
<ul>
<li>One practical coding assignment</li>
<li>Run your code against test cases</li>
<li>Answer a short follow-up review</li>
</ul>
<a href="{coding_url}"
   style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#6366f1);
   color:#fff;padding:14px 32px;text-decoration:none;border-radius:12px;
   font-weight:bold;font-size:16px;margin:16px 0">
   Start Coding Assessment
</a>
<p style="color:#a8a29e;font-size:12px">
This link is unique to you. Do not share it.
</p>
""")
        print(f"[ORCH] Coding assessment link sent to {candidate['email']}")
        log_agent("COMMUNICATOR", "email_sent", f"Coding assessment link → {candidate['email']}", candidate_id)
    except Exception as e:
        print(f"[ORCH] Coding link error: {e}")


def resume_pipeline_after_coding(candidate_id: str):
    print(f"\n[ORCH] ═══ CODING ROUTE: {candidate_id} ═══")
    log_agent("ORCHESTRATOR", "coding_complete", "Coding assessment finished — routing to technical", candidate_id)
    try:
        candidate = get_candidate(candidate_id)
        if not candidate:
            print(f"[ORCH] Candidate not found: {candidate_id}")
            return {"status": "missing_candidate"}

        job_id = candidate.get("job_id", "")
        hr_id  = candidate.get("hr_id", "")

        update_candidate(candidate_id, {"status": "waiting_technical_interview"})

        write_audit(candidate_id, "ORCHESTRATOR", "coding_complete_routed", {
            "job_id": job_id,
            "coding_score": candidate.get("coding_score")
        })

        log_agent("ORCHESTRATOR", "assigning_interviewer", "Matching best interviewer after coding", candidate_id)

        assign_result = _assign_interviewer(
            candidate_id, job_id, hr_id, "technical"
        )

        _notify_hr_of_progress(candidate_id, "coding_completed",
            f"Candidate completed coding and is being routed to technical interview.")

        print(f"[ORCH] Coding complete routed: {assign_result}")
        log_agent("ORCHESTRATOR", "technical_assigned", f"Interviewer assigned after coding: {assign_result.get('primary', 'N/A')}", candidate_id)
        return {"status": "waiting_technical_interview", "assignment": assign_result}
    except Exception as e:
        print(f"[ORCH] Coding resume error: {e}")
        log_agent("ORCHESTRATOR", "error", f"Coding route error: {str(e)[:50]}", candidate_id)
        return {"status": "error", "error": str(e)}