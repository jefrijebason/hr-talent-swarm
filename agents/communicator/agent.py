from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.cosmos_client import get_candidate, update_candidate, write_audit, add_to_talent_pool
from shared.config import config
from azure.communication.email import EmailClient
import json

def send_email(to_address: str, subject: str, body_html: str) -> bool:
    """Send email via Azure Communication Services."""
    try:
        email_client = EmailClient.from_connection_string(
            config.ACS_CONNECTION
        )
        message = {
            "senderAddress": config.ACS_EMAIL_SENDER,
            "recipients": {
                "to": [{"address": to_address}]
            },
            "content": {
                "subject": subject,
                "html": body_html
            }
        }
        poller = email_client.begin_send(message)
        result = poller.result()
        print(f"[COMM] Email sent to {to_address}")
        return True
    except Exception as e:
        print(f"[COMM] Email error: {e}")
        return False

def generate_offer_email(candidate: dict) -> dict:
    """Generate personalized offer letter using GPT-4o Mini."""
    prompt = f"""
Write a warm professional offer letter email.

Candidate Name:  {candidate.get('name')}
Role:            {candidate.get('applied_role')}
Agreed Salary:   {candidate.get('agreed_salary', 'To be confirmed')}
Start Date:      30 days from today

Include:
- Warm congratulations
- Role and team details
- Salary and benefits
- Start date
- Next steps (sign and return within 5 days)

Return ONLY valid JSON:
{{
    "subject": "email subject here",
    "body_html": "full html email body here"
}}
"""
    response = ask_gpt4o_mini(prompt)
    return parse_json(response)

def generate_rejection_email(candidate: dict) -> dict:
    """Generate personalized rejection email with feedback."""
    reasons = ", ".join(candidate.get("decision_reasons", []))
    prompt = f"""
Write a kind constructive rejection email with specific feedback.
Never use generic templates. Always be specific and helpful.

Candidate Name: {candidate.get('name')}
Role:           {candidate.get('applied_role')}
Feedback:       {reasons}

Include:
- Thank them for their time
- Specific feedback on what was strong
- Specific areas to improve
- Encouragement to apply again in 6 months
- Warm closing

Return ONLY valid JSON:
{{
    "subject": "email subject here",
    "body_html": "full html email body here"
}}
"""
    response = ask_gpt4o_mini(prompt)
    return parse_json(response)

def run_communicator(candidate_id: str, action: str) -> bool:
    """
    Main communicator function.
    action: HIRE or REJECT
    1. Get candidate from Cosmos DB
    2. Generate personalized email
    3. Send via ACS
    4. Update status
    5. Add to talent pool if near miss
    """
    print(f"[COMM] Starting for candidate: {candidate_id} | Action: {action}")

    candidate = get_candidate(candidate_id)

    if action == "HIRE":
        email_data = generate_offer_email(candidate)
        status = "hired"
    else:
        email_data = generate_rejection_email(candidate)
        status = "rejected"

        # Add to talent pool if score was above 60
        final_score = candidate.get("final_score", 0) or 0
        resume_score = candidate.get("resume_score", 0) or 0

        if final_score >= 60 or resume_score >= 60:
            add_to_talent_pool(candidate)
            print(f"[COMM] Added to talent pool")

    # Send email
    sent = send_email(
        to_address=candidate["email"],
        subject=email_data["subject"],
        body_html=email_data["body_html"]
    )

    # Update status
    update_candidate(candidate_id, {
        "status": status,
        "email_sent": sent
    })

    write_audit(candidate_id, "COMMUNICATOR", f"email_{action.lower()}", {
        "to": candidate["email"],
        "subject": email_data["subject"],
        "sent": sent
    })

    print(f"[COMM] Done. Email sent: {sent}")
    return sent