import msal
import requests
import json
from datetime import datetime, timedelta
from shared.config import config
from shared.cosmos_client import get_candidate, update_candidate, write_audit
from shared.service_bus import publish_human_gate

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
ORGANIZER_EMAIL = "JefriJebason@NET995.onmicrosoft.com"

TECHNICAL_INTERVIEWERS = ["jefrijebason@gmail.com"]
HR_INTERVIEWERS = ["jefrijebason@gmail.com"]


def get_access_token() -> str:
    try:
        app = msal.ConfidentialClientApplication(
            config.GRAPH_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{config.GRAPH_TENANT_ID}",
            client_credential=config.GRAPH_CLIENT_SECRET
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" in result:
            print("[SCHEDULER] Graph API token acquired")
            return result["access_token"]
        else:
            print(f"[SCHEDULER] Token error: {result.get('error_description')}")
            return None
    except Exception as e:
        print(f"[SCHEDULER] Auth error: {e}")
        return None


def _get_user_object_id(token: str) -> str:
    """Get the organizer's Object ID for app-only auth meeting creation."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{GRAPH_BASE}/users/{ORGANIZER_EMAIL}",
            headers=headers
        )
        if r.status_code == 200:
            user_id = r.json().get("id")
            print(f"[SCHEDULER] Organizer ID: {user_id[:8]}...")
            return user_id
        else:
            print(f"[SCHEDULER] User lookup failed: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"[SCHEDULER] User lookup error: {e}")
        return None


def create_teams_meeting(token: str,
                          slot: datetime,
                          attendees: list,
                          title: str,
                          candidate_name: str) -> dict:
    """Create a real Teams meeting using app-only auth."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    user_id = _get_user_object_id(token)
    if not user_id:
        print("[SCHEDULER] Cannot get organizer ID — skipping Teams meeting")
        return {"success": False, "error": "No organizer ID"}

    end_slot = slot + timedelta(hours=1)

    meeting_body = {
        "subject": title,
        "startDateTime": slot.strftime("%Y-%m-%dT%H:%M:%S") + "+05:30",
        "endDateTime":   end_slot.strftime("%Y-%m-%dT%H:%M:%S") + "+05:30",
        "participants": {
            "attendees": [
                {"upn": email, "role": "attendee"}
                for email in attendees if email
            ]
        }
    }

    try:
        response = requests.post(
            f"{GRAPH_BASE}/users/{user_id}/onlineMeetings",
            headers=headers,
            json=meeting_body
        )
        if response.status_code in [200, 201]:
            meeting = response.json()
            meeting_url = meeting.get("joinWebUrl", "")
            print(f"[SCHEDULER] Real Teams meeting created: {meeting_url[:60]}...")
            return {
                "success":     True,
                "meeting_url": meeting_url,
                "meeting_id":  meeting.get("id"),
                "slot":        slot.isoformat()
            }
        else:
            print(f"[SCHEDULER] Meeting error: {response.status_code} {response.text[:300]}")
            return {"success": False, "error": response.text[:300]}
    except Exception as e:
        print(f"[SCHEDULER] Meeting creation error: {e}")
        return {"success": False, "error": str(e)}


def get_best_slot(interview_type: str = "technical") -> datetime:
    if config.DEMO_MODE:
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        days = 1
        while True:
            slot = now + timedelta(days=days)
            slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
            if slot.weekday() < 5:
                print(f"[SCHEDULER] Demo slot: {slot}")
                return slot
            days += 1

    token = get_access_token()
    if not token:
        return _get_demo_slot()

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(days=7)
    headers = {"Authorization": f"Bearer {token}"}

    interviewers = (
        TECHNICAL_INTERVIEWERS
        if interview_type == "technical"
        else HR_INTERVIEWERS
    )

    try:
        response = requests.post(
            f"{GRAPH_BASE}/me/calendar/getSchedule",
            headers=headers,
            json={
                "schedules": interviewers,
                "startTime": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
                "endTime":   {"dateTime": end.isoformat(),   "timeZone": "Asia/Kolkata"},
                "availabilityViewInterval": 60
            }
        )
        if response.status_code == 200:
            schedules = response.json().get("value", [])
            for h in range(7 * 24):
                t = start + timedelta(hours=h)
                if 9 <= t.hour < 17 and t.weekday() < 5:
                    all_free = all(
                        len(s.get("availabilityView", "")) > h
                        and s["availabilityView"][h] == "0"
                        for s in schedules
                    )
                    if all_free:
                        print(f"[SCHEDULER] Free slot found: {t}")
                        return t
    except Exception as e:
        print(f"[SCHEDULER] Calendar error: {e}")

    return _get_demo_slot()


def _get_demo_slot() -> datetime:
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    slot = now + timedelta(days=1)
    slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
    return slot


def run_scheduler(candidate_id: str,
                  interview_type: str = "technical",
                  send_candidate_email: bool = True,
                  interviewer_email: str = "",
                  interviewer_name: str = "",
                  assignment_id: str = "") -> dict:
    """Main scheduler: books Teams meeting and dispatches emails."""
    print(f"[SCHEDULER] Scheduling {interview_type} interview for: {candidate_id}")

    candidate = get_candidate(candidate_id)
    name  = candidate.get("name", "Candidate")
    email = candidate.get("email")
    role  = candidate.get("applied_role", "Role")

    slot = get_best_slot(interview_type)

    if interview_type == "technical":
        attendees = TECHNICAL_INTERVIEWERS + [email]
        title  = f"Technical Interview — {name} | {role}"
        status = "technical_interview_scheduled"
    else:
        attendees = HR_INTERVIEWERS + [email]
        title  = f"HR Interview — {name} | {role}"
        status = "hr_interview_scheduled"

    if interviewer_email and interviewer_email not in attendees:
        attendees.append(interviewer_email)

    token = get_access_token()
    result = {"success": False, "meeting_url": "", "slot": slot.isoformat()}
    if token:
        result = create_teams_meeting(token, slot, attendees, title, name)

    meeting_url = result.get("meeting_url", "")
    if not result.get("success") or not meeting_url:
        print("[SCHEDULER] Teams meeting not created — using text-only fallback")
        meeting_url = "https://teams.live.com/meet/9367792243138?p=sZHbbDKnF227zfxcDK"

    slot_str = slot.strftime("%A %B %d, %Y at %I:%M %p IST")

    if interview_type == "technical":
        update_candidate(candidate_id, {
            "technical_interview_slot":            slot.isoformat(),
            "technical_interview_slot_human":      slot_str,
            "technical_interview_meeting_url":     meeting_url,
            "status": status
        })
    else:
        update_candidate(candidate_id, {
            "hr_interview_slot":            slot.isoformat(),
            "hr_interview_slot_human":      slot_str,
            "hr_interview_meeting_url":     meeting_url,
            "status": status
        })

    write_audit(candidate_id, "SCHEDULER",
                f"{interview_type}_interview_scheduled", {
        "slot": slot.isoformat(),
        "meeting_url": meeting_url,
        "attendees": attendees
    })

    if send_candidate_email:
        _send_interview_invite(candidate, slot_str, meeting_url, interview_type)

    if interviewer_email:
        _send_interviewer_invite(
            candidate, interviewer_name, interviewer_email,
            slot_str, meeting_url, interview_type, assignment_id
        )

    print(f"[SCHEDULER] Interview scheduled: {slot_str}")
    return {
        "slot":        slot.isoformat(),
        "slot_human":  slot_str,
        "meeting_url": meeting_url,
        "attendees":   attendees
    }


def _send_interview_invite(candidate: dict,
                            slot_str: str,
                            meeting_url: str,
                            interview_type: str):
    """Send interview invitation email to CANDIDATE."""
    from agents.communicator.agent import send_email

    interview_name = "Technical Interview" if interview_type == "technical" else "HR Discussion"
    meeting_section = (
        f"""<p><strong>Meeting link:</strong></p>
            <a href="{meeting_url}"
               style="display:inline-block;background:#6366f1;color:#fff;
               padding:12px 24px;text-decoration:none;border-radius:8px;
               font-weight:bold">Join Teams Meeting →</a>"""
        if meeting_url else
        """<p><strong>Meeting details:</strong><br>The interviewer will send you a
           calendar invite with the meeting link shortly.</p>"""
    )

    try:
        send_email(
            to_address=candidate.get("email"),
            subject=f"Invitation to {interview_name} for {candidate.get('applied_role', '')} Role",
            body_html=f"""
<p>Dear {candidate.get('name')},</p>
<p>We are pleased to invite you to the next stage of the recruitment process
for the <strong>{candidate.get('applied_role', '')}</strong> position.</p>
<p>Your {interview_name} is scheduled for
<strong>{slot_str}</strong> and will be conducted via Microsoft Teams.</p>

<p><strong>What to expect:</strong><br>
This 60-minute session will focus on assessing your technical skills,
problem-solving abilities, and knowledge relevant to the role.</p>

<p><strong>How to prepare:</strong><br>
Review key concepts relevant to the role, practice explaining your
thought process clearly, and prepare questions for the interviewer.</p>

{meeting_section}

<p>If you have questions or need to reschedule, please feel free to reach out.</p>
<p>Best regards,<br>Recruitment Team</p>
""")
        print(f"[SCHEDULER] Interview invite sent to {candidate.get('email')}")
    except Exception as e:
        print(f"[SCHEDULER] Invite email error: {e}")


def _send_interviewer_invite(candidate: dict,
                              interviewer_name: str,
                              interviewer_email: str,
                              slot_str: str,
                              meeting_url: str,
                              interview_type: str,
                              assignment_id: str = ""):
    """Send interview details + candidate AI briefing + RESUME PDF to INTERVIEWER."""
    from agents.communicator.agent import send_email, fetch_resume_attachment

    # ── NEW: fetch the candidate's resume PDF for attachment ──
    resume_attachment = fetch_resume_attachment(candidate)
    attachments = [resume_attachment] if resume_attachment else None

    ai_profile = candidate.get("ai_profile", {})
    briefing = ai_profile.get("human_interview_briefing", {})
    focus_on    = briefing.get("focus_on", [])
    do_not_test = briefing.get("do_not_test_again", [])
    suggestions = briefing.get("suggested_questions", [])

    meeting_section = ""
    if meeting_url:
        meeting_section = f"""
<p><a href="{meeting_url}"
   style="display:inline-block;background:#6366f1;color:#fff;
   padding:12px 24px;text-decoration:none;border-radius:8px;
   font-weight:bold">Join Teams Meeting →</a></p>
"""
    else:
        meeting_section = """
<p>A calendar invite with the Teams meeting link will follow shortly.</p>
"""

    if interview_type == "hr":
        decision_url = f"http://localhost:8000/hr/decision/{candidate.get('id','')}"
        meeting_section += f"""
<div style="margin-top:20px;padding:20px;background:#f8fafc;
border-radius:12px;border:1px solid #e2e8f0">
<p style="font-weight:700;color:#0f172a;margin:0 0 6px;font-size:15px">
    After the HR Interview
</p>
<p style="color:#64748b;font-size:13px;margin:0 0 14px">
    Once the interview is complete, use this form to send an offer,
    decline, or add the candidate to the talent pool.
</p>
<a href="{decision_url}"
    style="display:inline-block;background:linear-gradient(135deg,#6366f1,#7c3aed);
    color:#fff;padding:14px 28px;text-decoration:none;border-radius:8px;
    font-weight:700;font-size:14px">
    📋 Open Decision Form →
</a>
<p style="color:#94a3b8;font-size:11px;margin:10px 0 0">
    Options: Send Offer Letter · Decline · Add to Talent Pool
</p>
</div>"""

    # ── NEW: tell the interviewer the resume is attached (only if it actually is) ──
    resume_note_html = ""
    if resume_attachment:
        resume_note_html = """
<div style="margin-top:18px;padding:14px 18px;background:#eef2ff;
border-radius:10px;border-left:4px solid #6366f1">
<p style="margin:0;color:#1e1b4b;font-size:13px">
📎 <strong>Candidate's resume is attached</strong> to this email.
Please review it before the interview to prepare targeted questions.
</p>
</div>"""

    focus_html     = "".join(f"<li>{f}</li>" for f in focus_on[:5]) if focus_on else "<li>Technical depth and culture fit</li>"
    skip_html      = "".join(f"<li>{s}</li>" for s in do_not_test[:5]) if do_not_test else "<li>Basic skills already verified by AI</li>"
    questions_html = "".join(f"<li>{q}</li>" for q in suggestions[:3]) if suggestions else ""

    from shared.tokens import generate_token
    score_token = generate_token('score', assignment_id) if assignment_id else ''
    score_url = f"http://localhost:8000/interview/score/{assignment_id}?token={score_token}" if assignment_id else "#"

    try:
        send_email(
            to_address=interviewer_email,
            subject=f"Interview Assignment — {candidate.get('name')} | {candidate.get('applied_role', '')}",
            body_html=f"""
<h2>Interview Scheduled</h2>
<p>Hi {interviewer_name},</p>
<p>You have an interview scheduled:</p>

<table style="border-collapse:collapse;width:100%;max-width:500px">
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Candidate</td>
    <td style="padding:10px">{candidate.get('name')}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Role</td>
    <td style="padding:10px">{candidate.get('applied_role', '')}</td>
</tr>
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Date & Time</td>
    <td style="padding:10px">{slot_str}</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">AI Score</td>
    <td style="padding:10px">{candidate.get('ai_interview_score', 'N/A')}/100</td>
</tr>
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Resume Score</td>
    <td style="padding:10px">{candidate.get('resume_score', 'N/A')}/100</td>
</tr>
</table>

{meeting_section}

{resume_note_html}

<h3>AI Interview Briefing</h3>
<p><strong>Focus your interview on:</strong></p>
<ul>{focus_html}</ul>

<p><strong>Already tested by AI (skip these):</strong></p>
<ul>{skip_html}</ul>

{"<p><strong>Suggested questions:</strong></p><ul>" + questions_html + "</ul>" if questions_html else ""}

<p style="margin-top:24px"><strong>After the interview, submit your evaluation:</strong></p>
<a href="{score_url}"
   style="display:inline-block;background:#6366f1;color:#fff;padding:12px 28px;
   text-decoration:none;border-radius:8px;font-weight:bold">
   Submit Your Evaluation →
</a>

<p>Thank you,<br>HR Team</p>
""",
            attachments=attachments,   # ← NEW: resume PDF goes here
        )
        print(f"[SCHEDULER] Interviewer invite sent to {interviewer_email}"
              + (" with resume attached" if resume_attachment else " (no resume attached)"))
    except Exception as e:
        print(f"[SCHEDULER] Interviewer invite error: {e}")