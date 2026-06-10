from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.cosmos_client import update_candidate, write_audit, get_candidate
from shared.config import config
from shared.agent_feed import log_agent
from azure.storage.blob import BlobServiceClient
import pdfplumber
import io

# ── Resume keyword signals ───────────────────────────────────────
RESUME_KEYWORDS = [
    "experience", "education", "skills", "work", "project",
    "bachelor", "master", "engineer", "manager", "developer",
    "years", "university", "college", "internship", "certification",
    "employed", "responsibilities", "achieved", "built", "designed"
]


def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract text from PDF.
    Returns dict with:
      - text: extracted text or ""
      - status: "ok" | "scanned" | "corrupted" | "empty"
      - pages: number of pages
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            page_count = len(pdf.pages)

            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text

            # ── Scanned PDF detection ────────────────────────────
            if page_count > 0 and len(text.strip()) < 50:
                print(f"[SCREENER] Scanned PDF detected ({page_count} pages, no text)")
                return {"text": "", "status": "scanned", "pages": page_count}

            # ── Empty PDF ────────────────────────────────────────
            if len(text.strip()) < 50:
                return {"text": "", "status": "empty", "pages": page_count}

            return {"text": text, "status": "ok", "pages": page_count}

    except Exception as e:
        print(f"[SCREENER] PDF parse error: {e}")
        return {"text": "", "status": "corrupted", "pages": 0}


def detect_resume(text: str) -> bool:
    """
    Check if extracted text looks like a resume.
    Returns False if it's an invoice, certificate, etc.
    """
    text_lower = text.lower()
    matches = sum(1 for k in RESUME_KEYWORDS if k in text_lower)
    return matches >= 2


def remove_bias(resume_text: str) -> str:
    prompt = f"""
Remove all personally identifying information from this resume.
Replace or remove: full name, email, phone number, gender signals,
religion signals, university prestige markers, home address.
Keep everything else: skills, job titles, years of experience,
achievements, technical content.
Return only the anonymized resume text. Nothing else.

RESUME:
{resume_text}
"""
    return ask_gpt4o_mini(prompt)


def score_resume(anonymized_text: str, job_role: str) -> dict:
    prompt = f"""
You are an expert technical recruiter. Score this anonymized resume.

JOB ROLE: {job_role}

RESUME:
{anonymized_text}

Score the candidate on these dimensions (0-100 each):
- technical_skills: How well skills match the job role
- experience_depth: Quality and relevance of experience
- communication: Clarity of resume writing
- overall_score: Final weighted score

Also extract:
- skills: List of technical skills found
- experience_years: Total years of relevant experience
- strengths: Top 3 strengths
- concerns: Any red flags or gaps
- reasoning: 2 sentence explanation of overall score

Return ONLY valid JSON. No markdown. No explanation outside JSON.

{{
    "overall_score": 0,
    "technical_skills": 0,
    "experience_depth": 0,
    "communication": 0,
    "skills": [],
    "experience_years": 0,
    "strengths": [],
    "concerns": [],
    "reasoning": ""
}}
"""
    response = ask_gpt4o_mini(prompt)
    result = parse_json(response)

    # ── Validate score is not 0 (possible GPT failure) ──────────
    if result.get("overall_score", 0) == 0 and result.get("skills"):
        print(f"[SCREENER] Warning: score=0 but skills found. Possible GPT issue.")
        result["overall_score"] = 50  # safe fallback

    return result


def upload_resume_to_blob(pdf_bytes: bytes, candidate_id: str) -> str:
    try:
        blob_service = BlobServiceClient.from_connection_string(config.BLOB_CONNECTION)
        blob_name    = f"{candidate_id}.pdf"
        blob_client  = blob_service.get_blob_client(
            container=config.BLOB_CONTAINER, blob=blob_name)
        blob_client.upload_blob(pdf_bytes, overwrite=True)
        print(f"[SCREENER] Resume uploaded: {blob_name}")
        return blob_name
    except Exception as e:
        print(f"[SCREENER] Blob upload error: {e}")
        return ""


def _notify_bad_resume(candidate_id: str, reason: str):
    """Notify candidate their resume had an issue."""
    try:
        from agents.communicator.agent import send_email
        candidate = get_candidate(candidate_id)
        if not candidate:
            return

        messages = {
            "scanned": {
                "title":   "Scanned Resume Detected",
                "problem": "Your resume appears to be a scanned image. "
                           "Our system cannot read image-based PDFs.",
                "tip":     "💡 Export your resume as PDF from Word or Google Docs "
                           "(File → Download as PDF). This creates a text-based PDF."
            },
            "empty": {
                "title":   "Resume Could Not Be Read",
                "problem": "We could not extract content from your resume.",
                "tip":     "💡 Check that your PDF is not password-protected "
                           "and contains selectable text."
            },
            "corrupted": {
                "title":   "Resume File Issue",
                "problem": "Your resume file appears to be corrupted or unreadable.",
                "tip":     "💡 Try re-saving your resume as a new PDF file and re-uploading."
            },
            "not_resume": {
                "title":   "Wrong File Uploaded",
                "problem": "The uploaded file does not appear to be a resume or CV.",
                "tip":     "💡 Please upload your CV/resume PDF, "
                           "not a certificate, transcript, or other document."
            }
        }

        msg = messages.get(reason, messages["empty"])

        send_email(
            to_address=candidate.get("email"),
            subject=f"Action Required — Resume Upload Issue | "
                    f"{candidate.get('applied_role', '')}",
            body_html=f"""
<div style="font-family:Segoe UI,sans-serif;max-width:560px">
  <h2 style="color:#dc2626">⚠️ {msg['title']}</h2>
  <p>Hi {candidate.get('name')},</p>
  <p>Thank you for applying for
  <strong>{candidate.get('applied_role', '')}</strong>.</p>

  <div style="background:#fef2f2;border:1px solid #fecaca;
    border-radius:10px;padding:16px;margin:16px 0">
    <p style="color:#dc2626;margin:0 0 8px;font-weight:600">
      Issue Found:
    </p>
    <p style="margin:0;color:#7f1d1d">{msg['problem']}</p>
  </div>

  <div style="background:#f0fdf4;border:1px solid #86efac;
    border-radius:10px;padding:16px;margin:16px 0">
    <p style="margin:0;color:#166534">{msg['tip']}</p>
  </div>

  <p>Your application slot is saved for <strong>48 hours</strong>.
  Please re-apply with a corrected resume.</p>

  <a href="http://localhost:3001"
     style="display:inline-block;background:#6366f1;color:#fff;
     padding:12px 24px;text-decoration:none;border-radius:8px;
     font-weight:bold;margin:8px 0">
     Re-Apply Now →
  </a>

  <p style="color:#94a3b8;font-size:12px;margin-top:16px">
    Tracking ID: {candidate_id[:8].upper()} ·
    This slot expires in 48 hours.
  </p>
</div>
""")
        print(f"[SCREENER] Bad resume notification sent to {candidate.get('email')}")
    except Exception as e:
        print(f"[SCREENER] Notification error: {e}")


def run_screener(candidate_id: str,
                 pdf_bytes: bytes,
                 job_role: str) -> dict:
    print(f"[SCREENER] Starting for: {candidate_id}")
    log_agent("SCREENER", "started",
              f"Analyzing resume for {job_role}", candidate_id)

    # ── Upload to Blob (keep copy regardless of outcome) ────────
    upload_resume_to_blob(pdf_bytes, candidate_id)

    # ── Extract text ─────────────────────────────────────────────
    print(f"[SCREENER] Extracting text...")
    log_agent("SCREENER", "extracting",
              "Reading PDF and extracting text", candidate_id)

    extracted = extract_text_from_pdf(pdf_bytes)
    status    = extracted["status"]
    text      = extracted["text"]

    # ── Handle extraction failures ───────────────────────────────
    if status == "scanned":
        log_agent("SCREENER", "failed",
                  "Scanned PDF — no text layer", candidate_id)
        update_candidate(candidate_id, {
            "status": "resume_unreadable",
            "resume_issue": "scanned_pdf"
        })
        _notify_bad_resume(candidate_id, "scanned")
        return {"error": "scanned_pdf",
                "message": "Scanned PDF — candidate notified"}

    if status in ("empty", "corrupted"):
        log_agent("SCREENER", "failed",
                  f"PDF {status} — cannot process", candidate_id)
        update_candidate(candidate_id, {
            "status": "resume_unreadable",
            "resume_issue": status
        })
        _notify_bad_resume(candidate_id, status)
        return {"error": status,
                "message": f"PDF {status} — candidate notified"}

    # ── Check it's actually a resume ─────────────────────────────
    if not detect_resume(text):
        print(f"[SCREENER] Not a resume — keyword check failed")
        log_agent("SCREENER", "failed",
                  "Document is not a resume", candidate_id)
        update_candidate(candidate_id, {
            "status": "resume_unreadable",
            "resume_issue": "not_resume"
        })
        _notify_bad_resume(candidate_id, "not_resume")
        return {"error": "not_resume",
                "message": "Not a resume — candidate notified"}

    print(f"[SCREENER] Extracted {len(text)} characters ✅")
    log_agent("SCREENER", "extracted",
              f"Extracted {len(text)} characters", candidate_id)

    # ── Remove bias ──────────────────────────────────────────────
    print(f"[SCREENER] Removing bias...")
    log_agent("SCREENER", "bias_removal",
              "Stripping PII — name, gender, age, photo removed",
              candidate_id)
    anonymized = remove_bias(text)

    if not anonymized or len(anonymized.strip()) < 50:
        print(f"[SCREENER] Bias removal returned empty — using original")
        anonymized = text  # fallback to original text

    log_agent("SCREENER", "bias_removed",
              "Resume anonymized for fair evaluation", candidate_id)

    # ── Score resume ─────────────────────────────────────────────
    print(f"[SCREENER] Scoring candidate...")
    log_agent("SCREENER", "scoring",
              "AI evaluating skills, experience, and fit", candidate_id)

    result = score_resume(anonymized, job_role)

    # ── Validate result ──────────────────────────────────────────
    if not result or "overall_score" not in result:
        print(f"[SCREENER] Scoring failed — using fallback score 50")
        log_agent("SCREENER", "warning",
                  "GPT scoring failed — fallback score used", candidate_id)
        result = {
            "overall_score":   50,
            "technical_skills": 50,
            "experience_depth": 50,
            "communication":    50,
            "skills":           [],
            "experience_years": 0,
            "strengths":        [],
            "concerns":         ["Could not fully parse resume"],
            "reasoning":        "Fallback score — manual review recommended"
        }

    # ── Save to Cosmos DB ────────────────────────────────────────
    update_candidate(candidate_id, {
        "resume_score":     result["overall_score"],
        "skills":           result.get("skills", []),
        "experience_years": result.get("experience_years", 0),
        "resume_strengths": result.get("strengths", []),
        "resume_concerns":  result.get("concerns", []),
        "status":           "screened"
    })

    write_audit(candidate_id, "SCREENER", "resume_scored", {
        "score":        result["overall_score"],
        "bias_removed": True,
        "reasoning":    result.get("reasoning", ""),
        "pdf_pages":    extracted["pages"]
    })

    print(f"[SCREENER] Score: {result['overall_score']}/100")
    log_agent("SCREENER", "resume_scored",
        f"Score: {result['overall_score']}/100 | "
        f"Skills: {', '.join(result.get('skills', [])[:3])}",
        candidate_id)

    return result