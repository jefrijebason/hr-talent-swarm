from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.cosmos_client import get_candidate, update_candidate, write_audit, add_to_talent_pool
from shared.config import config
from shared.agent_feed import log_agent
from azure.communication.email import EmailClient
import json
import base64

# ════════════════════════════════════════════════════════════════════
# EMAIL SENDING — with optional PDF attachment support (ACS Email API)
# ════════════════════════════════════════════════════════════════════
def send_email(to_address: str,
                subject: str,
                body_html: str,
                attachments: list = None) -> bool:
    """
    Send email via Azure Communication Services.

    attachments format (optional):
      [{"name": "Resume.pdf",
        "contentType": "application/pdf",
        "contentInBase64": "<base64-encoded-bytes>"}]
    """
    try:
        email_client = EmailClient.from_connection_string(config.ACS_CONNECTION)
        message = {
            "senderAddress": config.ACS_EMAIL_SENDER,
            "recipients":    {"to": [{"address": to_address}]},
            "content":       {"subject": subject, "html": body_html}
        }
        if attachments:
            message["attachments"] = attachments
            print(f"[COMM] Attaching {len(attachments)} file(s) to email")

        poller = email_client.begin_send(message)
        result = poller.result()
        print(f"[COMM] Email sent to {to_address}")
        log_agent("COMMUNICATOR", "email_sent",
                  f"To: {to_address} | {subject[:50]}"
                  + (f" | with {len(attachments)} attachment(s)" if attachments else ""))
        return True
    except Exception as e:
        print(f"[COMM] Email error: {e}")
        log_agent("COMMUNICATOR", "email_failed",
                  f"To: {to_address} | Error: {str(e)[:50]}")
        return False


# ════════════════════════════════════════════════════════════════════
# RESUME ATTACHMENT HELPER — finds resume across possible storage shapes
# ════════════════════════════════════════════════════════════════════
def fetch_resume_attachment(candidate: dict) -> dict | None:
    """
    Try to fetch the candidate's resume PDF and return as ACS attachment dict.
    Returns None (gracefully) if no resume is found — email still goes out.

    Tries (in order):
      1. candidate.resume_base64       — already encoded in DB
      2. candidate.resume_url          — public/SAS URL → HTTP GET
      3. candidate.resume_blob_url     — public/SAS URL → HTTP GET
      4. candidate.resume_blob_name    — blob path → use BlobServiceClient
      5. candidate.resume_path         — same as above (alt field name)
    """
    candidate_name = candidate.get("name", "candidate").replace(" ", "_")
    filename = f"{candidate_name}_Resume.pdf"

    def _make_attachment(b64_string: str) -> dict:
        return {
            "name":            filename,
            "contentType":     "application/pdf",
            "contentInBase64": b64_string,
        }

    # 1. Already base64 in DB
    if candidate.get("resume_base64"):
        print(f"[COMM] Resume found inline (base64) for {candidate_name}")
        return _make_attachment(candidate["resume_base64"])

    # 2/3. Direct URL (public or SAS-signed)
    url = candidate.get("resume_url") or candidate.get("resume_blob_url")
    if url and url.startswith("http"):
        try:
            import requests
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and r.content:
                b64 = base64.b64encode(r.content).decode("utf-8")
                print(f"[COMM] Resume downloaded from URL ({len(r.content)} bytes)")
                return _make_attachment(b64)
            else:
                print(f"[COMM] Resume URL returned {r.status_code}")
        except Exception as e:
            print(f"[COMM] Resume URL fetch error: {e}")

    # 4/5. Blob name → use Azure Blob SDK
    blob_name = (candidate.get("resume_blob_name")
                 or candidate.get("resume_path")
                 or candidate.get("resume_blob"))
    if blob_name:
        try:
            from azure.storage.blob import BlobServiceClient
            blob_conn = (getattr(config, "BLOB_CONNECTION", None)
                         or getattr(config, "BLOB_CONNECTION_STRING", None)
                         or getattr(config, "AZURE_STORAGE_CONNECTION_STRING", None))
            container = (getattr(config, "RESUME_CONTAINER", None)
                         or getattr(config, "BLOB_CONTAINER", None)
                         or "resumes")
            if blob_conn:
                svc = BlobServiceClient.from_connection_string(blob_conn)
                bc  = svc.get_blob_client(container=container, blob=blob_name)
                data = bc.download_blob().readall()
                b64  = base64.b64encode(data).decode("utf-8")
                print(f"[COMM] Resume downloaded from Blob '{blob_name}' ({len(data)} bytes)")
                return _make_attachment(b64)
            else:
                print("[COMM] No BLOB_CONNECTION configured — cannot fetch resume")
        except Exception as e:
            print(f"[COMM] Blob resume fetch error: {e}")

    print(f"[COMM] No resume found for {candidate_name} — email will be sent without attachment")
    return None


# ════════════════════════════════════════════════════════════════════
# EXISTING FUNCTIONS — unchanged
# ════════════════════════════════════════════════════════════════════
def generate_offer_email(candidate: dict) -> dict:
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
    print(f"[COMM] Starting for candidate: {candidate_id} | Action: {action}")
    log_agent("COMMUNICATOR", "started", f"Preparing {action} email", candidate_id)

    candidate = get_candidate(candidate_id)

    if action == "HIRE":
        log_agent("COMMUNICATOR", "generating_offer",
                  f"Creating offer letter for {candidate.get('name')}", candidate_id)
        email_data = generate_offer_email(candidate)
        status = "hired"
    else:
        log_agent("COMMUNICATOR", "generating_rejection",
                  f"Creating feedback email for {candidate.get('name')}", candidate_id)
        email_data = generate_rejection_email(candidate)
        status = "rejected"

        final_score = candidate.get("final_score", 0) or 0
        resume_score = candidate.get("resume_score", 0) or 0

        if final_score >= 60 or resume_score >= 60:
            add_to_talent_pool(candidate)
            print(f"[COMM] Added to talent pool")
            log_agent("COMMUNICATOR", "talent_pool",
                      f"{candidate.get('name')} saved for future roles", candidate_id)

    sent = send_email(
        to_address=candidate["email"],
        subject=email_data["subject"],
        body_html=email_data["body_html"]
    )

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
    log_agent("COMMUNICATOR", "complete",
              f"{action} email {'sent' if sent else 'failed'} to {candidate.get('name')}",
              candidate_id)
    return sent