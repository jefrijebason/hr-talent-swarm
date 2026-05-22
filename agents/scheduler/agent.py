import msal
import requests
import json
from datetime import datetime, timedelta
from shared.config import config
from shared.cosmos_client import get_candidate, update_candidate, write_audit
from shared.service_bus import publish_human_gate

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# ── Demo interviewers ────────────────────────────────────────────
# For hackathon demo — use real outlook accounts you control
# Create 2 free outlook.com accounts for demo purposes
TECHNICAL_INTERVIEWERS = [
    "jefrijebason@gmail.com"   # Replace with real interviewer email
]

HR_INTERVIEWERS = [
    "jefrijebason@gmail.com"   # Replace with real HR email
]

def get_access_token() -> str:
    """Get Microsoft Graph API access token."""
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

def create_teams_meeting(token: str,
                          slot: datetime,
                          attendees: list,
                          title: str,
                          candidate_name: str) -> dict:
    """Create a Teams meeting at the given slot."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json"
    }

    end_slot = slot + timedelta(hours=1)

    attendee_list = [
        {
            "emailAddress": {"address": email},
            "type": "required"
        }
        for email in attendees
    ]

    event_body = {
        "subject": title,
        "body": {
            "contentType": "HTML",
            "content": f"""
                <h2>Interview Scheduled</h2>
                <p>This is your interview with <strong>{candidate_name}</strong>.</p>
                <p>Please join via the Teams link below.</p>
                <p>Duration: 60 minutes</p>
            """
        },
        "start": {
            "dateTime": slot.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_slot.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Asia/Kolkata"
        },
        "attendees": attendee_list,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    try:
        response = requests.post(
            f"{GRAPH_BASE}/me/events",
            headers=headers,
            json=event_body
        )

        if response.status_code in [200, 201]:
            event = response.json()
            meeting_url = event.get(
                "onlineMeeting", {}
            ).get("joinUrl", "")
            print(f"[SCHEDULER] Teams meeting created: {meeting_url}")
            return {
                "success":     True,
                "meeting_url": meeting_url,
                "event_id":    event.get("id"),
                "slot":        slot.isoformat()
            }
        else:
            print(f"[SCHEDULER] Meeting error: {response.text}")
            return {"success": False, "error": response.text}

    except Exception as e:
        print(f"[SCHEDULER] Meeting creation error: {e}")
        return {"success": False, "error": str(e)}

def get_best_slot(interview_type: str = "technical") -> datetime:
    """
    Get best available interview slot.
    In demo mode — returns next business day at 10 AM.
    In production — reads real calendars via Graph API.
    """
    if config.DEMO_MODE:
        # Demo mode — return next weekday at 10 AM IST
        now  = datetime.utcnow() + timedelta(hours=5, minutes=30)
        days = 1
        while True:
            slot = now + timedelta(days=days)
            slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
            # Skip weekends
            if slot.weekday() < 5:
                print(f"[SCHEDULER] Demo slot: {slot}")
                return slot
            days += 1

    # Production mode — read real calendars
    token = get_access_token()
    if not token:
        # Fallback to demo slot
        return get_best_slot_demo()

    # Find overlapping free slots
    start  = datetime.utcnow() + timedelta(days=1)
    end    = start + timedelta(days=7)
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
                "startTime": {
                    "dateTime": start.isoformat(),
                    "timeZone": "Asia/Kolkata"
                },
                "endTime": {
                    "dateTime": end.isoformat(),
                    "timeZone": "Asia/Kolkata"
                },
                "availabilityViewInterval": 60
            }
        )

        if response.status_code == 200:
            schedules = response.json().get("value", [])
            # Find first free slot between 9am-5pm on weekdays
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

    # Fallback
    return get_best_slot_demo()

def get_best_slot_demo() -> datetime:
    """Fallback demo slot."""
    now  = datetime.utcnow() + timedelta(hours=5, minutes=30)
    slot = now + timedelta(days=1)
    slot = slot.replace(hour=10, minute=0, second=0, microsecond=0)
    return slot

def run_scheduler(candidate_id: str,
                  interview_type: str = "technical") -> dict:
    """
    Main scheduler function.
    Books Teams meeting for technical or HR interview.
    interview_type: "technical" or "hr"
    """
    print(f"[SCHEDULER] Scheduling {interview_type} interview for: {candidate_id}")

    candidate = get_candidate(candidate_id)
    name      = candidate.get("name", "Candidate")
    email     = candidate.get("email")
    role      = candidate.get("applied_role", "Role")

    # Get best slot
    slot = get_best_slot(interview_type)

    # Set up attendees and title
    if interview_type == "technical":
        attendees = TECHNICAL_INTERVIEWERS + [email]
        title     = f"Technical Interview — {name} | {role}"
        status    = "technical_interview_scheduled"
    else:
        attendees = HR_INTERVIEWERS + [email]
        title     = f"HR Interview — {name} | {role}"
        status    = "hr_interview_scheduled"

    # Try to create Teams meeting
    token  = get_access_token()
    result = {"success": False, "meeting_url": "", "slot": slot.isoformat()}

    if token:
        result = create_teams_meeting(
            token, slot, attendees, title, name
        )

    # If Teams creation fails — use demo URL
    if not result.get("success"):
        print("[SCHEDULER] Using demo meeting URL")
        result = {
            "success":     True,
            "meeting_url": "https://teams.microsoft.com/demo-meeting-link",
            "slot":        slot.isoformat()
        }

    # Save to Cosmos DB
    slot_str = slot.strftime("%A %B %d, %Y at %I:%M %p IST")

    if interview_type == "technical":
        update_candidate(candidate_id, {
            "technical_interview_slot":        slot.isoformat(),
            "technical_interview_slot_human":  slot_str,
            "technical_interview_meeting_url": result.get("meeting_url"),
            "status": status
        })
    else:
        update_candidate(candidate_id, {
            "hr_interview_slot":        slot.isoformat(),
            "hr_interview_slot_human":  slot_str,
            "hr_interview_meeting_url": result.get("meeting_url"),
            "status": status
        })

    write_audit(candidate_id, "SCHEDULER",
                f"{interview_type}_interview_scheduled", {
        "slot":        slot.isoformat(),
        "meeting_url": result.get("meeting_url"),
        "attendees":   attendees
    })

    # Send calendar invite email to candidate
    _send_interview_invite(
        candidate, slot_str,
        result.get("meeting_url"),
        interview_type
    )

    print(f"[SCHEDULER] Interview scheduled: {slot_str}")
    return {
        "slot":        slot.isoformat(),
        "slot_human":  slot_str,
        "meeting_url": result.get("meeting_url"),
        "attendees":   attendees
    }

def _send_interview_invite(candidate: dict,
                            slot_str: str,
                            meeting_url: str,
                            interview_type: str):
    """Send interview invitation email to candidate."""
    from shared.openai_client import ask_gpt4o_mini, parse_json
    from agents.communicator.agent import send_email

    interview_name = (
        "Technical Interview"
        if interview_type == "technical"
        else "HR Discussion"
    )

    prompt = f"""
Write a professional interview invitation email.

Candidate: {candidate.get('name')}
Interview type: {interview_name}
Slot: {slot_str}
Teams link: {meeting_url}
Role: {candidate.get('applied_role')}

Include:
- What to expect in this round
- How to prepare
- Teams meeting link
- Duration: 60 minutes

Return ONLY valid JSON:
{{
    "subject": "email subject",
    "body_html": "html email body"
}}
"""

    try:
        response   = ask_gpt4o_mini(prompt)
        email_data = parse_json(response)
        send_email(
            to_address=candidate.get("email"),
            subject=email_data.get("subject"),
            body_html=email_data.get("body_html")
        )
        print(f"[SCHEDULER] Interview invite sent to {candidate.get('email')}")
    except Exception as e:
        print(f"[SCHEDULER] Invite email error: {e}")