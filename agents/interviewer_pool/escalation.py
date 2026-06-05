from shared.cosmos_client import (
    get_assignment, update_assignment,
    get_interviewer, get_candidate,
    get_job, get_hr_user,
    add_assignment_timeline,
    save_assignment, update_candidate,
    update_interviewer
)
from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.config import config
from agents.communicator.agent import send_email
from datetime import datetime, timedelta
import uuid

# ── Escalation Timings (hours) ───────────────────────────────────
DEFAULT_RESPONSE_HRS   = 2
DEFAULT_ESCALATION_HRS = 2
DEFAULT_HR_ALERT_HRS   = 5

def _base_url() -> str:
    return getattr(config, 'PUBLIC_URL', 'http://localhost:8000')

def create_assignment(candidate_id: str,
                       job_id: str,
                       hr_id: str,
                       match_result: dict,
                       interview_type: str = "technical") -> dict:
    """Create interview assignment with full escalation chain."""
    now = datetime.utcnow()

    job = get_job(job_id)
    response_hrs = job.get("primary_response_hrs", DEFAULT_RESPONSE_HRS) if job else DEFAULT_RESPONSE_HRS

    primary  = match_result.get("primary")
    backup_1 = match_result.get("backup_1")
    backup_2 = match_result.get("backup_2")

    assignment = {
        "id":               str(uuid.uuid4()),
        "candidate_id":     candidate_id,
        "job_id":           job_id,
        "hr_id":            hr_id,
        "interview_type":   interview_type,
        "primary_interviewer_id": primary.get("id") if primary else None,
        "backup_1_id":      backup_1.get("id") if backup_1 else None,
        "backup_2_id":      backup_2.get("id") if backup_2 else None,
        "assigned_to":      primary.get("id") if primary else None,
        "status":           "pending",
        "escalation_level": 0,
        "created_at":       now.isoformat(),
        "response_deadline": (now + timedelta(hours=response_hrs)).isoformat(),
        "hr_alerted":       False,
        "feedback_submitted": False,
        "timeline": [{
            "time":   now.isoformat(),
            "event":  "assignment_created",
            "detail": f"Primary: {primary.get('name', 'None') if primary else 'None'}"
        }]
    }

    save_assignment(assignment)
    print(f"[PIS] Assignment created: {assignment['id']}")
    return assignment

def send_interview_request(assignment_id: str) -> bool:
    """Send interview request to currently assigned interviewer."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return False

    interviewer_id = assignment.get("assigned_to")
    if not interviewer_id:
        return False

    interviewer = get_interviewer(interviewer_id)
    candidate   = get_candidate(assignment["candidate_id"])

    if not interviewer or not candidate:
        return False

    hr = get_hr_user(assignment.get("hr_id", ""))
    hr_name  = hr.get("name", "HR Team") if hr else "HR Team"
    hr_email = hr.get("email", "") if hr else ""

    ai_profile  = candidate.get("ai_profile", {})
    briefing    = ai_profile.get("human_interview_briefing", {})
    focus_on    = briefing.get("focus_on", [])
    do_not_test = briefing.get("do_not_test_again", [])
    suggestions = briefing.get("suggested_questions", [])

    base_url    = _base_url()
    accept_url  = f"{base_url}/api/assignments/{assignment_id}/accept"
    decline_url = f"{base_url}/api/assignments/{assignment_id}/decline"

    prompt = f"""
Write a professional interview request email to an interviewer.

INTERVIEWER: {interviewer['name']}
CANDIDATE: {candidate['name']}
ROLE: {candidate['applied_role']}
AI SCORE: {candidate.get('ai_interview_score', 'N/A')}/100
CANDIDATE SKILLS: {', '.join(candidate.get('skills', []))}

AI ALREADY TESTED (do NOT re-test):
{', '.join(do_not_test) if do_not_test else 'Basic technical skills'}

FOCUS YOUR INTERVIEW ON:
{', '.join(focus_on) if focus_on else 'Technical depth and culture fit'}

SUGGESTED QUESTIONS:
{chr(10).join(suggestions[:3]) if suggestions else 'See candidate profile'}

ACCEPT LINK: {accept_url}
DECLINE LINK: {decline_url}

HR CONTACT: {hr_name} ({hr_email})
RESPONSE DEADLINE: 2 hours

Write a clear professional email.
Include all briefing details.
Include ACCEPT and DECLINE buttons clearly as HTML links.
Duration: 45 minutes.

Return ONLY valid JSON:
{{
    "subject": "email subject",
    "body_html": "complete html email"
}}
"""

    try:
        response   = ask_gpt4o_mini(prompt)
        email_data = parse_json(response)

        sent = send_email(
            to_address=interviewer["email"],
            subject=email_data.get("subject",
                f"Interview Request — {candidate['name']} | {candidate['applied_role']}"),
            body_html=email_data.get("body_html", "")
        )

        if sent:
            update_assignment(assignment_id, {
                "status":      "invited",
                "assigned_at": datetime.utcnow().isoformat()
            })
            add_assignment_timeline(
                assignment_id, "invitation_sent",
                f"Email sent to {interviewer['name']} ({interviewer['email']})"
            )
            print(f"[PIS] Invitation sent to {interviewer['name']}")

        return sent

    except Exception as e:
        print(f"[PIS] Email error: {e}")
        return False

def check_and_escalate(assignment_id: str) -> dict:
    """Check deadline and escalate to next level if needed."""
    assignment = get_assignment(assignment_id)
    if not assignment:
        return {"status": "not_found"}

    status = assignment.get("status")
    if status in ["accepted", "completed"]:
        return {"status": "already_handled"}

    deadline_str = assignment.get("response_deadline")
    if not deadline_str:
        return {"status": "no_deadline"}

    deadline = datetime.fromisoformat(deadline_str)
    now      = datetime.utcnow()

    if now < deadline:
        remaining = (deadline - now).seconds // 60
        return {"status": "waiting", "minutes_remaining": remaining}

    level = assignment.get("escalation_level", 0)
    print(f"[PIS] Deadline passed. Escalation level: {level}")

    if level == 0:
        return _escalate_to_backup1(assignment_id, assignment)
    elif level == 1:
        return _escalate_to_backup2(assignment_id, assignment)
    elif level == 2:
        return _alert_hr(assignment_id, assignment)
    else:
        return {"status": "max_escalation_reached"}

def _escalate_to_backup1(assignment_id: str, assignment: dict) -> dict:
    """Escalate to backup 1."""
    backup_id = assignment.get("backup_1_id")
    if not backup_id:
        return _alert_hr(assignment_id, assignment)

    backup = get_interviewer(backup_id)
    if not backup:
        return _alert_hr(assignment_id, assignment)

    job = get_job(assignment["job_id"])
    escalation_hrs = job.get("escalation_response_hrs", DEFAULT_ESCALATION_HRS) if job else DEFAULT_ESCALATION_HRS

    _notify_skipped_interviewer(assignment, level=0)

    update_assignment(assignment_id, {
        "assigned_to":       backup_id,
        "escalation_level":  1,
        "status":            "pending",
        "response_deadline": (datetime.utcnow() + timedelta(hours=escalation_hrs)).isoformat()
    })

    add_assignment_timeline(
        assignment_id, "escalated_to_backup1",
        f"Primary did not respond. Escalated to {backup['name']}"
    )

    _update_candidate_status(assignment["candidate_id"],
        "Your interview is being scheduled. Confirmation soon.")

    send_interview_request(assignment_id)
    print(f"[PIS] Escalated to backup 1: {backup['name']}")
    return {"status": "escalated_to_backup1", "interviewer": backup["name"]}

def _escalate_to_backup2(assignment_id: str, assignment: dict) -> dict:
    """Escalate to backup 2."""
    backup_id = assignment.get("backup_2_id")
    if not backup_id:
        return _alert_hr(assignment_id, assignment)

    backup = get_interviewer(backup_id)
    if not backup:
        return _alert_hr(assignment_id, assignment)

    job = get_job(assignment["job_id"])
    escalation_hrs = job.get("escalation_response_hrs", DEFAULT_ESCALATION_HRS) if job else DEFAULT_ESCALATION_HRS

    _notify_skipped_interviewer(assignment, level=1)

    update_assignment(assignment_id, {
        "assigned_to":       backup_id,
        "escalation_level":  2,
        "status":            "pending",
        "response_deadline": (datetime.utcnow() + timedelta(hours=escalation_hrs)).isoformat()
    })

    add_assignment_timeline(
        assignment_id, "escalated_to_backup2",
        f"Backup 1 did not respond. Escalated to {backup['name']}"
    )

    _update_candidate_status(assignment["candidate_id"],
        "We are prioritizing your interview scheduling.")

    send_interview_request(assignment_id)
    print(f"[PIS] Escalated to backup 2: {backup['name']}")
    return {"status": "escalated_to_backup2", "interviewer": backup["name"]}

def _alert_hr(assignment_id: str, assignment: dict) -> dict:
    """All interviewers failed — alert the HR who posted the JD."""
    hr_id = assignment.get("hr_id")
    hr    = get_hr_user(hr_id) if hr_id else None

    if not hr:
        print(f"[PIS] No HR found for assignment {assignment_id}")
        return {"status": "no_hr_found"}

    candidate = get_candidate(assignment["candidate_id"])

    tried = []
    for key in ["primary_interviewer_id", "backup_1_id", "backup_2_id"]:
        iid = assignment.get(key)
        if iid:
            iv = get_interviewer(iid)
            if iv:
                tried.append(iv["name"])

    base_url          = _base_url()
    custom_assign_url = f"{base_url}/api/assignments/{assignment_id}/custom-assign"
    extend_url        = f"{base_url}/api/assignments/{assignment_id}/extend"

    prompt = f"""
Write an URGENT email to an HR manager.
All interviewers are unavailable.
HR must manually assign an interviewer.

HR NAME: {hr['name']}
CANDIDATE: {candidate['name']}
ROLE: {candidate['applied_role']}
AI SCORE: {candidate.get('ai_interview_score', 'N/A')}/100
WAITING SINCE: {assignment['created_at']}
INTERVIEWERS TRIED: {', '.join(tried)}

ACTIONS HR CAN TAKE:
1. Custom assign URL: {custom_assign_url}
   (HR enters any email + name to send invitation)
2. Extend timeline URL: {extend_url}
   (Give 48 more hours and retry automatically)

This is URGENT. Candidate SLA at risk.
The email should feel urgent but professional.
Give clear action buttons.

Return ONLY valid JSON:
{{
    "subject": "urgent subject line",
    "body_html": "complete html email with clear action buttons"
}}
"""

    try:
        response   = ask_gpt4o_mini(prompt)
        email_data = parse_json(response)

        send_email(
            to_address=hr["email"],
            subject=email_data.get("subject",
                f"⚠️ Action Required: Interview not scheduled for {candidate['name']}"),
            body_html=email_data.get("body_html", "")
        )

        update_assignment(assignment_id, {
            "escalation_level": 3,
            "hr_alerted":       True,
            "hr_alerted_at":    datetime.utcnow().isoformat(),
            "status":           "hr_action_required"
        })

        add_assignment_timeline(
            assignment_id, "hr_alerted",
            f"All interviewers unavailable. HR {hr['name']} alerted."
        )

        _update_candidate_status(
            assignment["candidate_id"],
            "Our HR team is personally handling your interview scheduling. "
            "You will hear from us within 4 hours."
        )

        print(f"[PIS] HR alerted: {hr['name']} ({hr['email']})")
        return {"status": "hr_alerted", "hr": hr["name"]}

    except Exception as e:
        print(f"[PIS] HR alert error: {e}")
        return {"status": "alert_failed", "error": str(e)}

def handle_custom_assign(assignment_id: str,
                          custom_email: str,
                          custom_name: str) -> bool:
    """HR manually assigns a custom interviewer."""
    assignment = get_assignment(assignment_id)
    candidate  = get_candidate(assignment["candidate_id"])

    base_url    = _base_url()
    accept_url  = f"{base_url}/api/assignments/{assignment_id}/accept"
    decline_url = f"{base_url}/api/assignments/{assignment_id}/decline"

    prompt = f"""
Write a personal interview invitation email.
This person is being personally assigned by HR.
Make it feel important and respectful.

TO: {custom_name}
CANDIDATE: {candidate['name']}
ROLE: {candidate['applied_role']}
DURATION: 45 minutes
ACCEPT: {accept_url}
DECLINE: {decline_url}

Note: Once they accept they join the interviewer pool.

Return ONLY valid JSON:
{{
    "subject": "subject",
    "body_html": "html email"
}}
"""

    try:
        response   = ask_gpt4o_mini(prompt)
        email_data = parse_json(response)

        sent = send_email(
            to_address=custom_email,
            subject=email_data.get("subject", "Interview Request"),
            body_html=email_data.get("body_html", "")
        )

        if sent:
            update_assignment(assignment_id, {
                "custom_assignee_email": custom_email,
                "custom_assignee_name":  custom_name,
                "assigned_to":           f"custom_{custom_email}",
                "status":                "invited",
                "response_deadline": (datetime.utcnow() + timedelta(hours=4)).isoformat()
            })
            add_assignment_timeline(
                assignment_id, "custom_assigned",
                f"HR manually assigned: {custom_name} ({custom_email})"
            )

        return sent

    except Exception as e:
        print(f"[PIS] Custom assign error: {e}")
        return False

def handle_acceptance(assignment_id: str) -> bool:
    """Interviewer accepted. Schedule meeting. Notify both parties."""
    assignment     = get_assignment(assignment_id)
    candidate      = get_candidate(assignment["candidate_id"])
    interviewer_id = assignment.get("assigned_to", "")

    if interviewer_id.startswith("custom_"):
        interviewer_name  = assignment.get("custom_assignee_name", "Interviewer")
        interviewer_email = assignment.get("custom_assignee_email", "")
    else:
        iv = get_interviewer(interviewer_id)
        interviewer_name  = iv["name"] if iv else "Interviewer"
        interviewer_email = iv["email"] if iv else ""

    # Schedule meeting — send emails to BOTH candidate AND interviewer
    from agents.scheduler.agent import run_scheduler
    try:
        slot = run_scheduler(
            assignment["candidate_id"],
            assignment["interview_type"],
            send_candidate_email=True,
            interviewer_email=interviewer_email,
            interviewer_name=interviewer_name
        )
        meeting_url = slot.get("meeting_url", "")
        slot_human  = slot.get("slot_human", "")
    except Exception as e:
        print(f"[PIS] Scheduler error: {e}")
        meeting_url = ""
        slot_human  = "To be confirmed"

    update_assignment(assignment_id, {
        "status":             "accepted",
        "accepted_at":        datetime.utcnow().isoformat(),
        "meeting_url":        meeting_url,
        "meeting_slot_human": slot_human
    })

    add_assignment_timeline(
        assignment_id, "accepted",
        f"{interviewer_name} accepted the interview"
    )

    # Do NOT call _send_candidate_confirmation here
    # run_scheduler already sent emails to both parties

    if not interviewer_id.startswith("custom_"):
        iv = get_interviewer(interviewer_id)
        if iv:
            update_interviewer(interviewer_id, {
                "current_booked": iv.get("current_booked", 0) + 1
            })

    print(f"[PIS] Accepted by {interviewer_name}. Meeting: {slot_human}")
    return True

def _notify_skipped_interviewer(assignment: dict, level: int):
    """Politely notify interviewer they were skipped."""
    key = "primary_interviewer_id" if level == 0 else "backup_1_id"
    iid = assignment.get(key)
    if not iid:
        return

    iv        = get_interviewer(iid)
    candidate = get_candidate(assignment["candidate_id"])
    if not iv or not candidate:
        return

    try:
        send_email(
            to_address=iv["email"],
            subject=f"Interview Reassigned — {candidate['name']}",
            body_html=f"""
<p>Hi {iv['name']},</p>
<p>The interview request for <strong>{candidate['name']}</strong>
has been reassigned as we did not receive a response
within the scheduled window.</p>
<p>No action needed from you.</p>
<p>HR Team</p>
"""
        )
    except Exception:
        pass

def _update_candidate_status(candidate_id: str, message: str):
    """Send proactive update to candidate."""
    try:
        candidate = get_candidate(candidate_id)
        send_email(
            to_address=candidate["email"],
            subject="Interview Update — Your Application",
            body_html=f"""
<p>Hi {candidate['name']},</p>
<p>{message}</p>
<p>Thank you for your patience.
We value your time and are working to
get this scheduled as quickly as possible.</p>
<p>Tracking ID: {candidate_id[:8].upper()}</p>
<p>HR Team</p>
"""
        )
        update_candidate(candidate_id, {
            "last_candidate_update": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"[PIS] Candidate update error: {e}")

def _send_candidate_confirmation(candidate_id: str,
                                  interviewer_name: str,
                                  slot_human: str,
                                  meeting_url: str,
                                  role: str):
    """Send interview confirmation to candidate."""
    candidate = get_candidate(candidate_id)
    try:
        send_email(
            to_address=candidate["email"],
            subject=f"✅ Interview Confirmed — {role}",
            body_html=f"""
<h2>Your Interview is Confirmed!</h2>
<p>Hi {candidate['name']},</p>
<p>Your technical interview has been scheduled.</p>
<table style="border-collapse:collapse;width:100%">
<tr><td style="padding:8px;font-weight:bold">Interviewer</td>
    <td style="padding:8px">{interviewer_name}</td></tr>
<tr><td style="padding:8px;font-weight:bold">Date & Time</td>
    <td style="padding:8px">{slot_human}</td></tr>
<tr><td style="padding:8px;font-weight:bold">Duration</td>
    <td style="padding:8px">45 minutes</td></tr>
<tr><td style="padding:8px;font-weight:bold">Platform</td>
    <td style="padding:8px">Microsoft Teams</td></tr>
</table>
<br>
<a href="{meeting_url}"
   style="background:#6366f1;color:#fff;padding:12px 24px;
          text-decoration:none;border-radius:8px;font-weight:bold">
  Join Teams Meeting →
</a>
<br><br>
<p><strong>Tips to prepare:</strong></p>
<ul>
<li>Review your past projects — expect deep questions</li>
<li>Think about system design at scale</li>
<li>Prepare questions to ask the interviewer</li>
</ul>
<p>Good luck! We are rooting for you.</p>
<p>HR Team</p>
"""
        )
    except Exception as e:
        print(f"[PIS] Confirmation email error: {e}")