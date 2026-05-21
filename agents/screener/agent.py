from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.cosmos_client import update_candidate, write_audit
from shared.config import config
from azure.storage.blob import BlobServiceClient
import pdfplumber
import io

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF resume."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        print(f"[SCREENER] PDF error: {e}")
        # Try reading as plain text
        try:
            return pdf_bytes.decode("utf-8")
        except Exception:
            return ""

def remove_bias(resume_text: str) -> str:
    """Remove identifying information from resume."""
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
    """Score candidate resume using GPT-4o Mini."""
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
    return parse_json(response)

def upload_resume_to_blob(pdf_bytes: bytes,
                          candidate_id: str) -> str:
    """Upload resume to Azure Blob Storage."""
    try:
        blob_service = BlobServiceClient.from_connection_string(
            config.BLOB_CONNECTION
        )
        blob_name   = f"{candidate_id}.pdf"
        blob_client = blob_service.get_blob_client(
            container=config.BLOB_CONTAINER,
            blob=blob_name
        )
        blob_client.upload_blob(pdf_bytes, overwrite=True)
        print(f"[SCREENER] Resume uploaded: {blob_name}")
        return blob_name
    except Exception as e:
        print(f"[SCREENER] Blob upload error: {e}")
        return ""

def run_screener(candidate_id: str,
                 pdf_bytes: bytes,
                 job_role: str) -> dict:
    """
    Main screener function.
    Works with both real PDFs and plain text.
    """
    print(f"[SCREENER] Starting for: {candidate_id}")

    # Upload to Blob Storage
    upload_resume_to_blob(pdf_bytes, candidate_id)

    # Extract text — handles both PDF and plain text
    print(f"[SCREENER] Extracting text...")
    resume_text = extract_text_from_pdf(pdf_bytes)

    if not resume_text or len(resume_text.strip()) < 50:
        print(f"[SCREENER] Could not extract text")
        return {"error": "Could not read resume"}

    print(f"[SCREENER] Extracted {len(resume_text)} characters")

    # Remove bias
    print(f"[SCREENER] Removing bias...")
    anonymized = remove_bias(resume_text)

    # Score resume
    print(f"[SCREENER] Scoring candidate...")
    result = score_resume(anonymized, job_role)

    # Save to Cosmos DB
    update_candidate(candidate_id, {
        "resume_score":    result["overall_score"],
        "skills":          result["skills"],
        "experience_years": result["experience_years"],
        "status":          "screened"
    })

    write_audit(candidate_id, "SCREENER", "resume_scored", {
        "score":        result["overall_score"],
        "bias_removed": True,
        "reasoning":    result["reasoning"]
    })

    print(f"[SCREENER] Score: {result['overall_score']}/100")
    return result