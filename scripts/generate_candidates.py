import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cosmos_client import save_candidate, update_candidate
from agents.screener.agent import run_screener
from agents.interviewer.agent import run_ai_interview
from agents.evaluator.agent import run_evaluator
from agents.communicator.agent import run_communicator
import uuid
import json
import time
import pdfplumber
import io

JD_TEXT = """
Senior AI Engineer — AI Platform Team

Requirements:
- 4 plus years Python experience
- Azure AI services experience
- Experience building production ML systems
- Knowledge of multi-agent AI systems
- Strong problem-solving skills
- Team leadership experience

Salary: 18-24 LPA
Location: Bangalore (Hybrid)
"""

CANDIDATES = [
    {
        "name":         "Arjun Mehta",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543210",
        "expected_ctc": "20 LPA",
        "resume_pdf":   "data/synthetic/strong_resume.pdf",
        "profile_type": "strong"
    },
    {
        "name":         "Priya Sharma",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543211",
        "expected_ctc": "18 LPA",
        "resume_pdf":   "data/synthetic/strong_resume.pdf",
        "profile_type": "strong"
    },
    {
        "name":         "Rahul Verma",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543212",
        "expected_ctc": "22 LPA",
        "resume_pdf":   "data/synthetic/strong_resume.pdf",
        "profile_type": "strong"
    },
    {
        "name":         "Sneha Patel",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543213",
        "expected_ctc": "15 LPA",
        "resume_pdf":   "data/synthetic/borderline_resume.pdf",
        "profile_type": "borderline"
    },
    {
        "name":         "Karan Singh",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543214",
        "expected_ctc": "16 LPA",
        "resume_pdf":   "data/synthetic/borderline_resume.pdf",
        "profile_type": "borderline"
    },
    {
        "name":         "Ravi Kumar",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543215",
        "expected_ctc": "12 LPA",
        "resume_pdf":   "data/synthetic/reject_resume.pdf",
        "profile_type": "reject"
    },
    {
        "name":         "Deepa Nair",
        "email":        "jefrijebason@gmail.com",
        "phone":        "9876543216",
        "expected_ctc": "10 LPA",
        "resume_pdf":   "data/synthetic/reject_resume.pdf",
        "profile_type": "reject"
    },
]

def get_resume_text(pdf_path: str) -> str:
    """Extract text from PDF."""
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        print(f"  PDF read error: {e}")
        return ""

def process_candidate(info: dict) -> str:
    """Process one candidate through pipeline."""
    candidate_id = str(uuid.uuid4())

    # Check PDF exists
    if not os.path.exists(info["resume_pdf"]):
        print(f"  PDF not found: {info['resume_pdf']}")
        return None

    # Read PDF
    with open(info["resume_pdf"], "rb") as f:
        pdf_bytes = f.read()

    # Save to Cosmos DB
    candidate = {
        "id":           candidate_id,
        "name":         info["name"],
        "email":        info["email"],
        "phone":        info["phone"],
        "applied_role": "Senior AI Engineer",
        "expected_ctc": info["expected_ctc"],
        "status":       "applied",
        "profile_type": info["profile_type"]
    }
    save_candidate(candidate)

    # Screen resume
    screen_result = run_screener(
        candidate_id,
        pdf_bytes,
        "Senior AI Engineer"
    )
    resume_score = screen_result.get("overall_score", 0)
    print(f"  Resume Score: {resume_score}/100")

    # Below threshold — reject
    if resume_score < 60:
        run_communicator(candidate_id, "REJECT")
        print(f"  → Auto rejected (low score)")
        return candidate_id

    # Get resume text for interview
    resume_text = get_resume_text(info["resume_pdf"])

    # Run AI interview
    interview_result = run_ai_interview(
        candidate_id,
        resume_text,
        JD_TEXT
    )
    ai_score = interview_result.get("score", 0)
    print(f"  AI Score:     {ai_score}/100")

    # Simulate human decisions by profile type
    profile_type = info["profile_type"]

    if profile_type == "strong":
        update_candidate(candidate_id, {
            "human_tech_score":    8.5,
            "human_culture_score": 8.0,
            "agreed_salary":       "21 LPA",
            "human_notes":         "Strong candidate. Recommend hire.",
            "status":              "evaluating"
        })
        eval_result = run_evaluator(candidate_id)
        decision    = eval_result.get("decision", "HIRE")
        run_communicator(
            candidate_id,
            "HIRE" if decision == "HIRE" else "REJECT"
        )
        print(f"  → {decision}")

    elif profile_type == "borderline":
        update_candidate(candidate_id, {
            "human_tech_score":    5.5,
            "human_culture_score": 6.0,
            "agreed_salary":       "15 LPA",
            "human_notes":         "Borderline. Not enough depth.",
            "status":              "evaluating"
        })
        run_evaluator(candidate_id)
        run_communicator(candidate_id, "REJECT")
        print(f"  → Rejected after human review")

    else:
        run_evaluator(candidate_id)
        run_communicator(candidate_id, "REJECT")
        print(f"  → Rejected")

    return candidate_id

# ── Main ────────────────────────────────────────────────
print("=" * 55)
print("Generating Synthetic Candidates")
print("=" * 55)

generated = []

for i, info in enumerate(CANDIDATES):
    print(f"\n[{i+1}/{len(CANDIDATES)}] {info['name']} ({info['profile_type']})")

    try:
        cid = process_candidate(info)
        if cid:
            generated.append({
                "id":           cid,
                "name":         info["name"],
                "profile_type": info["profile_type"]
            })
            print(f"  ✓ ID: {cid}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    time.sleep(2)

# Save list
with open("data/synthetic/processed_candidates.json", "w") as f:
    json.dump(generated, f, indent=2)

print("\n" + "=" * 55)
print(f"✓ Processed {len(generated)} candidates")
print("Check Cosmos DB for all records")
print("Check Gmail for emails sent")
print("=" * 55)