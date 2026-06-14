"""
agents/scheduler/agent.py

UPDATED: Now injects ARIA's comprehensive AI interview briefing into the
interviewer assignment email. Everything else preserved:
  - Teams meeting creation
  - Resume PDF attachment
  - HR decision form link
  - Evaluation submission link
  - Candidate notification email

Backwards-compatible: if a candidate doesn't have the new `interview_briefing`
field, falls back to the legacy `ai_profile.human_interview_briefing` structure.
"""

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

    # ── AUTO-DISCOVER INTERVIEWER EMAIL if not provided ──
    if not interviewer_email:
        try:
            from shared.cosmos_client import get_all_interviewers
            all_iv = get_all_interviewers() or []

            # Prefer interviewers matching the type, fall back to anyone
            wanted_type = "hr_round" if interview_type != "technical" else "technical"
            preferred = [
                iv for iv in all_iv
                if iv.get("email") and (
                    wanted_type in (iv.get("roles") or [])
                    or iv.get("interview_type") == wanted_type
                    or iv.get("can_do_hr") if interview_type != "technical" else iv.get("can_do_technical")
                )
            ]
            chosen = (preferred or all_iv)[0] if (preferred or all_iv) else None
            if chosen:
                interviewer_email = chosen.get("email", "")
                interviewer_name  = chosen.get("name", "Interviewer")
                print(f"[SCHEDULER] Auto-picked {interview_type} interviewer: {interviewer_email}")
        except Exception as e:
            print(f"[SCHEDULER] Interviewer auto-discovery failed: {e}")

    # ── Auto-generate an assignment_id if missing, so the evaluation link works ──
    if interviewer_email and not assignment_id:
        try:
            import uuid as _uuid
            from shared.cosmos_client import save_assignment
            assignment_id = str(_uuid.uuid4())
            save_assignment({
                "id": assignment_id,
                "candidate_id": candidate_id,
                "assigned_to": "auto",
                "interview_type": interview_type if interview_type != "technical" else "technical",
                "status": "scheduled",
                "scheduled_at": slot.isoformat(),
                "meeting_url": meeting_url,
                "custom_assignee_email": interviewer_email,
                "custom_assignee_name":  interviewer_name or "Interviewer",
                "created_at": datetime.utcnow().isoformat(),
            })
            print(f"[SCHEDULER] Auto-created assignment {assignment_id[:8]}... for evaluation link")
        except Exception as e:
            print(f"[SCHEDULER] Could not create auto-assignment: {e}")

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


# ═══════════════════════════════════════════════════════════════════════
# UPDATED: _send_interviewer_invite now embeds the full ARIA briefing
# ═══════════════════════════════════════════════════════════════════════
def _send_interviewer_invite(candidate: dict,
                              interviewer_name: str,
                              interviewer_email: str,
                              slot_str: str,
                              meeting_url: str,
                              interview_type: str,
                              assignment_id: str = ""):
    """
    Send interview details + AI briefing + resume PDF to INTERVIEWER.

    The briefing HTML comes from ARIA's `format_briefing_for_email()` and includes:
      - Composite score + verdict badge
      - 5-dimension scoring table
      - Anti-cheat severity notes (if any)
      - Strengths / concerns / red flags
      - Resume validation table
      - Focus areas for human round
      - Already-tested skills (skip these)
      - Suggested questions
      - Collapsible full transcript
    """
    from agents.communicator.agent import send_email, fetch_resume_attachment
    from shared.tokens import generate_token

    # ── Fetch candidate's resume PDF for attachment ──
    resume_attachment = fetch_resume_attachment(candidate)
    attachments = [resume_attachment] if resume_attachment else None

    # ── Build the ARIA briefing HTML block ──
    briefing_html = _build_briefing_html(candidate)

    # ── Meeting section ──
    if meeting_url:
        meeting_section = f"""
<div style="background:#fff;border-radius:14px;padding:22px;margin:14px 0;
border:1px solid #e2e8f0;text-align:center">
  <p style="margin:0 0 14px;font-size:14px;color:#475569">
    Click below to join the interview at the scheduled time.
  </p>
  <a href="{meeting_url}"
     style="display:inline-block;background:linear-gradient(135deg,#6366f1,#4f46e5);
            color:#fff;padding:14px 32px;text-decoration:none;border-radius:11px;
            font-weight:700;font-size:15px">
    Join Teams Meeting →
  </a>
</div>"""
    else:
        meeting_section = """
<div style="background:#fff;border-radius:14px;padding:22px;margin:14px 0;
border:1px solid #e2e8f0;text-align:center">
  <p style="margin:0;color:#64748b;font-size:14px">
    A calendar invite with the Teams meeting link will follow shortly.
  </p>
</div>"""

    # ── HR decision form (only for HR interviews) ──
    decision_section = ""
    if interview_type == "hr":
        decision_url = f"http://localhost:8000/hr/decision/{candidate.get('id','')}"
        decision_section = f"""
<div style="margin:14px 0;padding:22px;background:#fff;
border-radius:14px;border:1px solid #e2e8f0">
  <p style="font-weight:700;color:#0f172a;margin:0 0 6px;font-size:15px">
    After the HR Interview
  </p>
  <p style="color:#64748b;font-size:13px;margin:0 0 14px">
    Once the interview is complete, use this form to send an offer,
    decline, or add the candidate to the talent pool.
  </p>
  <a href="{decision_url}"
     style="display:inline-block;background:linear-gradient(135deg,#6366f1,#7c3aed);
     color:#fff;padding:14px 28px;text-decoration:none;border-radius:11px;
     font-weight:700;font-size:14px">
    📋 Open Decision Form →
  </a>
  <p style="color:#94a3b8;font-size:11px;margin:10px 0 0">
    Options: Send Offer Letter · Decline · Add to Talent Pool
  </p>
</div>"""

    # ── Resume attached note ──
    resume_note_html = ""
    if resume_attachment:
        resume_note_html = """
<div style="margin:14px 0;padding:14px 18px;background:#eef2ff;
border-radius:10px;border-left:4px solid #6366f1">
  <p style="margin:0;color:#1e1b4b;font-size:13px">
    📎 <strong>Candidate's resume is attached</strong> to this email.
    Please review it before the interview.
  </p>
</div>"""

    # ── Evaluation submission link ──
    score_token = generate_token('score', assignment_id) if assignment_id else ''
    score_url = (
        f"http://localhost:8000/interview/score/{assignment_id}?token={score_token}"
        if assignment_id else "#"
    )
    evaluation_section = f"""
<div style="margin:14px 0;padding:22px;background:#fff;
border-radius:14px;border:1px solid #e2e8f0;text-align:center">
  <p style="font-weight:700;color:#0f172a;margin:0 0 6px;font-size:15px">
    Submit Your Evaluation
  </p>
  <p style="color:#64748b;font-size:13px;margin:0 0 14px">
    After the interview, score the candidate and leave your notes.
  </p>
  <a href="{score_url}"
     style="display:inline-block;background:#0f172a;color:#fff;
     padding:13px 28px;text-decoration:none;border-radius:11px;
     font-weight:700;font-size:14px">
    Submit Your Evaluation →
  </a>
</div>"""

    # ── Pull AI score for the subject line ──
    briefing_data = candidate.get("interview_briefing") or {}
    ai_score = briefing_data.get("composite_score") or candidate.get("ai_interview_score")

    subject = f"🎯 Interview Brief: {candidate.get('name')} — {candidate.get('applied_role', '')}"
    if ai_score is not None:
        subject += f" (AI Score: {ai_score}/100)"

    # ── Build the full email body ──
    body_html = f"""
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:720px;
margin:0 auto;background:#f1f5f9;padding:24px">

  <!-- Header -->
  <div style="background:#fff;border-radius:14px;padding:22px;margin-bottom:14px">
    <div style="font-size:11px;color:#5b8def;font-weight:700;
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px">
      🎯 Interview Assignment
    </div>
    <h2 style="margin:0 0 6px;font-size:20px;color:#0f172a">
      You've been invited to interview <strong>{candidate.get('name')}</strong>
    </h2>
    <div style="font-size:14px;color:#64748b">
      Role: <strong style="color:#0f172a">{candidate.get('applied_role', '')}</strong>
    </div>
  </div>

  <!-- Quick facts table -->
  <div style="background:#fff;border-radius:14px;padding:22px;margin-bottom:14px">
    <table style="border-collapse:collapse;width:100%;font-size:13px">
      <tr>
        <td style="padding:8px;color:#64748b;font-weight:600;width:140px">Date &amp; Time</td>
        <td style="padding:8px;color:#0f172a">{slot_str}</td>
      </tr>
      <tr style="background:#f8fafc">
        <td style="padding:8px;color:#64748b;font-weight:600">AI Interview Score</td>
        <td style="padding:8px;color:#0f172a;font-weight:700">{ai_score or 'N/A'}/100</td>
      </tr>
      <tr>
        <td style="padding:8px;color:#64748b;font-weight:600">Resume Score</td>
        <td style="padding:8px;color:#0f172a">{candidate.get('resume_score', 'N/A')}/100</td>
      </tr>
    </table>
  </div>

  <!-- Meeting -->
  {meeting_section}

  <!-- Resume attached note -->
  {resume_note_html}

  <!-- ARIA's full AI interview briefing -->
  {briefing_html}

  <!-- HR decision form (only for HR interviews) -->
  {decision_section}

  <!-- Evaluation submission -->
  {evaluation_section}

  <!-- Footer -->
  <div style="font-size:11px;color:#94a3b8;text-align:center;margin-top:18px">
    Generated by HR Swarm · ARIA AI Interviewer
  </div>

</div>
"""

    try:
        send_email(
            to_address=interviewer_email,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
        )
        print(f"[SCHEDULER] Interviewer invite sent to {interviewer_email}"
              + (" with resume + AI briefing" if resume_attachment else " (no resume)"))
    except Exception as e:
        print(f"[SCHEDULER] Interviewer invite error: {e}")


def _build_briefing_html(candidate: dict) -> str:
    """
    Build the AI briefing HTML block for the interviewer email.

    Priority:
      1. NEW structure: candidate.interview_briefing — produced by ARIA agent.
         Renders via format_briefing_for_email() (rich 5-dimension report).
      2. LEGACY structure: candidate.ai_profile.human_interview_briefing.
         Renders via _legacy_briefing_html() (simpler bullet list).
      3. NEITHER: skip the section gracefully.
    """
    # 1. Try NEW briefing structure (from ARIA agent)
    new_briefing = candidate.get("interview_briefing")
    if new_briefing and isinstance(new_briefing, dict):
        try:
            from agents.aria_interviewer.briefing_generator import format_briefing_for_email
            return format_briefing_for_email(new_briefing)
        except ImportError:
            print("[SCHEDULER] aria_interviewer not installed — falling back to legacy briefing format")
        except Exception as e:
            print(f"[SCHEDULER] format_briefing_for_email failed: {e}")

    # 2. Legacy fallback
    legacy = (candidate.get("ai_profile") or {}).get("human_interview_briefing")
    if legacy:
        return _legacy_briefing_html(legacy)

    # 3. Nothing to render
    return ""


def _legacy_briefing_html(briefing: dict) -> str:
    """Old briefing format — kept for backward compat with pre-ARIA candidates."""
    focus_on    = briefing.get("focus_on", [])
    do_not_test = briefing.get("do_not_test_again", [])
    suggestions = briefing.get("suggested_questions", [])

    focus_html = (
        "".join(f"<li style='margin-bottom:6px;color:#1e40af'>→ {f}</li>" for f in focus_on[:5])
        if focus_on else
        "<li style='color:#64748b'>Technical depth and culture fit</li>"
    )
    skip_html = (
        "".join(f"<li style='margin-bottom:6px;color:#475569'>✓ {s}</li>" for s in do_not_test[:5])
        if do_not_test else
        "<li style='color:#64748b'>Basic skills already verified by AI</li>"
    )
    questions_section = ""
    if suggestions:
        items = "".join(f"<li style='margin-bottom:6px;color:#1e40af'>→ {q}</li>" for q in suggestions[:3])
        questions_section = f"""
<div style="margin:14px 0">
  <div style="font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">
    💡 Suggested Questions
  </div>
  <ul style="margin:0;padding-left:4px;list-style:none">{items}</ul>
</div>"""

    return f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:24px;margin:14px 0">
  <div style="font-size:11px;color:#5b8def;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">
    🤖 AI Interview Briefing (legacy format)
  </div>

  <div style="margin:14px 0">
    <div style="font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">
      🎯 Focus your interview on
    </div>
    <ul style="margin:0;padding-left:4px;list-style:none">{focus_html}</ul>
  </div>

  <div style="margin:14px 0">
    <div style="font-size:12px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">
      ✓ Already tested by AI (skip these)
    </div>
    <ul style="margin:0;padding-left:4px;list-style:none">{skip_html}</ul>
  </div>

  {questions_section}
</div>
"""