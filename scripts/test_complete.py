import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator.agent import (
    create_candidate,
    run_ai_pipeline,
    technical_interview_result,
    hr_interview_result
)
from agents.interviewer.agent import run_coding_assessment
from shared.cosmos_client import get_candidate

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

RESUME_TEXT = """
Arjun Mehta — Senior AI Engineer

SKILLS:
Python 6 years, Azure ML, Azure OpenAI,
FastAPI, Docker, Kubernetes, PostgreSQL,
Machine Learning, NLP, REST APIs, Git

EXPERIENCE:
Senior AI Engineer — Tech Company (2022-2026)
Built ML pipelines processing 1M records daily
Deployed GPT-4 powered applications on Azure
Led team of 5 engineers
Reduced model inference time by 60 percent

AI Engineer — Startup (2020-2022)
Built NLP models for text classification
Deployed models using Docker and Kubernetes

EDUCATION:
M.Tech Artificial Intelligence (2020)

ACHIEVEMENTS:
Azure AI Engineer certification
Published 2 research papers on NLP
"""

print("=" * 55)
print("COMPLETE END TO END TEST")
print("=" * 55)

# Step 1 — Create candidate
print("\n[1] Creating candidate...")
candidate_id = create_candidate(
    name="Arjun Mehta",
    email="jefrijebason@gmail.com",
    phone="9876543210",
    applied_role="Senior AI Engineer",
    expected_ctc="20 LPA"
)
print(f"    ID: {candidate_id}")

# Step 2 — Run AI pipeline
print("\n[2] Running AI pipeline...")
ai_result = run_ai_pipeline(
    candidate_id,
    RESUME_TEXT.encode("utf-8"),
    "Senior AI Engineer",
    JD_TEXT
)
print(f"    Status: {ai_result.get('status')}")
print(f"    Resume: {ai_result.get('resume_score')}/100")
print(f"    AI:     {ai_result.get('ai_score')}/100")

# Step 3 — Simulate Technical Interview
print("\n[3] Technical Interview — HR clicks PASS...")
tech_result = technical_interview_result(
    candidate_id=candidate_id,
    tech_score=8.5,
    system_design_score=8.0,
    notes="Strong technical depth. Good system design. Recommend proceed.",
    passed=True
)
print(f"    Status: {tech_result.get('status')}")

# Step 4 — Simulate HR Interview
print("\n[4] HR Interview — HR clicks HIRE...")
hr_result = hr_interview_result(
    candidate_id=candidate_id,
    culture_score=8.0,
    communication_score=8.5,
    agreed_salary="21 LPA",
    notes="Excellent cultural fit. Strong communicator. Motivated by impact.",
    hired=True
)
print(f"    Status:   {hr_result.get('status')}")
print(f"    Decision: {hr_result.get('decision')}")
print(f"    Score:    {hr_result.get('final_score')}/100")

# Step 5 — Final check
print("\n[5] Final candidate record...")
final = get_candidate(candidate_id)
print(f"    Name:          {final.get('name')}")
print(f"    Resume Score:  {final.get('resume_score')}/100")
print(f"    AI Interview:  {final.get('ai_interview_score')}/100")
print(f"    Human Tech:    {final.get('human_tech_score')}/10")
print(f"    Human Culture: {final.get('human_culture_score')}/10")
print(f"    Final Score:   {final.get('final_score')}/100")
print(f"    Decision:      {final.get('decision')}")
print(f"    Status:        {final.get('status')}")
print(f"\nCheck Gmail for offer email!")
print("=" * 55)
print("✓ Complete test done!")