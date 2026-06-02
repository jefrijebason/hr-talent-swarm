from shared.config import config
from shared.cosmos_client import (
    save_interviewer, get_interviewer,
    get_interviewer_by_email,
    get_all_interviewers, update_interviewer,
    get_candidate, get_job, get_hr_user
)
from agents.communicator.agent import send_email
from agents.interviewer_pool.matcher import match_interviewers
from agents.interviewer_pool.escalation import (
    create_assignment, send_interview_request,
    check_and_escalate, handle_acceptance,
    handle_custom_assign
)
from shared.openai_client import ask_gpt4o_mini, parse_json
from datetime import datetime
import uuid
import secrets

def add_interviewer(name: str,
                    email: str,
                    role: str,
                    department: str,
                    seniority: str,
                    skills: list,
                    max_per_week: int,
                    added_by_hr_id: str) -> dict:
    """
    HR adds a new interviewer.
    Sends invitation email.
    Status starts as pending until they accept.
    """
    print(f"[POOL] Adding interviewer: {name}")

    # Check if already exists
    existing = get_interviewer_by_email(email)
    if existing:
        print(f"[POOL] Interviewer already exists: {email}")
        return existing

    invite_token = secrets.token_urlsafe(32)
    base_url     = getattr(config, 'PUBLIC_URL', 'http://localhost:8000')
    accept_url   = f"{base_url}/api/interviewers/onboard/{invite_token}"
    decline_url  = f"{base_url}/api/interviewers/decline/{invite_token}"

    interviewer = {
        "id":               str(uuid.uuid4()),
        "name":             name,
        "email":            email,
        "role":             role,
        "department":       department,
        "seniority":        seniority,
        "status":           "pending",
        "expertise_skills": skills,
        "max_per_week":     max_per_week,
        "current_booked":   0,
        "total_done":       0,
        "avg_rating":       0.0,
        "response_rate":    100.0,
        "avg_response_hrs": 0.0,
        "timezone":         "Asia/Kolkata",
        "invite_token":     invite_token,
        "added_by_hr_id":   added_by_hr_id,
        "created_at":       datetime.utcnow().isoformat()
    }

    save_interviewer(interviewer)

    # Send invitation email
    _send_invitation_email(
        interviewer, accept_url, decline_url, added_by_hr_id
    )

    print(f"[POOL] Invitation sent to {email}")
    return interviewer

def _send_invitation_email(interviewer: dict,
                            accept_url: str,
                            decline_url: str,
                            hr_id: str):
    """Send interviewer onboarding invitation."""
    hr = get_hr_user(hr_id)
    hr_name = hr.get("name", "HR Team") if hr else "HR Team"

    prompt = f"""
Write a professional interviewer invitation email.

TO: {interviewer['name']}
FROM HR: {hr_name}
ROLE ASKED TO INTERVIEW FOR: {interviewer['role']} level candidates
SKILLS: {', '.join(interviewer['expertise_skills'])}
COMMITMENT: {interviewer['max_per_week']} interviews per week max
DURATION: 45 minutes per interview
ACCEPT URL: {accept_url}
DECLINE URL: {decline_url}

Include:
- Why they were selected (their expertise)
- What the commitment involves
- What they get (AI briefing before each interview)
- Clear ACCEPT and DECLINE buttons
- Link expires in 48 hours

Return ONLY valid JSON:
{{
    "subject": "email subject",
    "body_html": "complete html email"
}}
"""

    try:
        response   = ask_gpt4o_mini(prompt)
        email_data = parse_json(response)
        send_email(
            to_address=interviewer["email"],
            subject=email_data.get("subject",
                "You have been invited to join our Interview Panel"),
            body_html=email_data.get("body_html", "")
        )
    except Exception as e:
        print(f"[POOL] Invitation email error: {e}")

def activate_interviewer(invite_token: str) -> dict:
    """
    Interviewer clicked ACCEPT in email.
    Activate them in the pool.
    """
    # Find by token
    all_iv = get_all_interviewers()
    interviewer = next(
        (iv for iv in all_iv
         if iv.get("invite_token") == invite_token),
        None
    )

    if not interviewer:
        return {"error": "Invalid or expired token"}

    updated = update_interviewer(interviewer["id"], {
        "status":    "active",
        "joined_at": datetime.utcnow().isoformat()
    })

    # Send welcome email
    send_email(
        to_address=interviewer["email"],
        subject="Welcome to the Interview Panel! 🎉",
        body_html=f"""
<h2>Welcome aboard, {interviewer['name']}!</h2>
<p>You are now an active interviewer in our system.</p>
<p>What happens next:</p>
<ul>
<li>You will receive interview requests by email</li>
<li>Each request includes full candidate AI briefing</li>
<li>You have 2 hours to accept or decline each request</li>
<li>Interviews are 45 minutes via Microsoft Teams</li>
<li>Please submit feedback within 24 hours after each interview</li>
</ul>
<p>Thank you for helping us build a great team!</p>
<p>HR Team</p>
"""
    )

    print(f"[POOL] Interviewer activated: {interviewer['name']}")
    return updated

def assign_interviewer_to_candidate(candidate_id: str,
                                     job_id: str,
                                     hr_id: str,
                                     interview_type: str = "technical") -> dict:
    """
    Main function: Match + assign + send invitation.
    Called by orchestrator after AI interview.
    """
    print(f"[POOL] Assigning interviewer for: {candidate_id}")

    candidate = get_candidate(candidate_id)
    job       = get_job(job_id)

    skills   = candidate.get("skills", [])
    category = candidate.get("jd_intelligence", {}).get(
        "role_category", "software_development"
    ) if candidate.get("jd_intelligence") else "software_development"
    seniority = candidate.get("jd_intelligence", {}).get(
        "seniority_level", "mid"
    ) if candidate.get("jd_intelligence") else "mid"

    # Match interviewers
    match_result = match_interviewers(
        skills, category, seniority, job_id
    )

    if not match_result.get("primary"):
        print("[POOL] No interviewers available — alerting HR directly")
        _alert_hr_no_interviewers(candidate_id, job_id, hr_id)
        return {"status": "no_interviewers", "hr_alerted": True}

    # Create assignment
    assignment = create_assignment(
        candidate_id, job_id, hr_id,
        match_result, interview_type
    )

    # Send invitation to primary
    send_interview_request(assignment["id"])

    return {
        "status":      "assigned",
        "assignment_id": assignment["id"],
        "primary":     match_result["primary"]["name"]
                       if match_result.get("primary") else None,
        "backup_1":    match_result["backup_1"]["name"]
                       if match_result.get("backup_1") else None,
        "backup_2":    match_result["backup_2"]["name"]
                       if match_result.get("backup_2") else None
    }

def _alert_hr_no_interviewers(candidate_id: str,
                                job_id: str,
                                hr_id: str):
    """Alert HR immediately when no interviewers available."""
    hr        = get_hr_user(hr_id)
    candidate = get_candidate(candidate_id)

    if not hr or not candidate:
        return

    send_email(
        to_address=hr["email"],
        subject=f"⚠️ No Interviewers Available — {candidate['name']}",
        body_html=f"""
<h2>Action Required</h2>
<p>Hi {hr['name']},</p>
<p>Candidate <strong>{candidate['name']}</strong> has passed
the AI interview with a score of
<strong>{candidate.get('ai_interview_score', 'N/A')}/100</strong>
and is ready for technical interview.</p>
<p><strong>Problem:</strong> There are no active interviewers
in the pool with matching skills.</p>
<p><strong>Action needed:</strong></p>
<ol>
<li>Add interviewers to the pool in your dashboard</li>
<li>Or manually assign someone using the link below</li>
</ol>
<a href="http://localhost:3000"
   style="background:#dc2626;color:#fff;padding:12px 24px;
          text-decoration:none;border-radius:8px">
  Go to Dashboard →
</a>
<p>The candidate has been waiting. Please act quickly.</p>
<p>HR Swarm System</p>
"""
    )

def get_pool_status() -> dict:
    """Get current interviewer pool status."""
    all_iv   = get_all_interviewers()
    active   = [iv for iv in all_iv if iv.get("status") == "active"]
    pending  = [iv for iv in all_iv if iv.get("status") == "pending"]
    inactive = [iv for iv in all_iv if iv.get("status") == "inactive"]

    available = [
        iv for iv in active
        if iv.get("current_booked", 0) < iv.get("max_per_week", 3)
    ]

    return {
        "total":     len(all_iv),
        "active":    len(active),
        "pending":   len(pending),
        "inactive":  len(inactive),
        "available": len(available),
        "interviewers": all_iv
    }