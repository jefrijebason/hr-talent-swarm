import sys
import os
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cosmos_client import save_candidate
from shared.openai_client import ask_gpt4o_mini, parse_json
from shared.cosmos_client import update_candidate, write_audit

# Create a test candidate in database
candidate_id = str(uuid.uuid4())

test_candidate = {
    "id": candidate_id,
    "name": "Test Candidate",
    "email": "test@example.com",
    "applied_role": "Senior AI Engineer",
    "status": "applied"
}

save_candidate(test_candidate)
print(f"✓ Test candidate created: {candidate_id}")

# Test resume as plain text
resume_text = """
John Smith
Software Engineer with 5 years experience

SKILLS:
Python, Azure, FastAPI, Docker, Machine Learning,
PostgreSQL, Git, REST APIs, Kubernetes

EXPERIENCE:
Senior Software Engineer - Tech Company (2021-2026)
- Built ML pipelines using Python and Azure ML
- Deployed microservices using Docker and Kubernetes
- Developed REST APIs using FastAPI

Software Engineer - Startup (2019-2021)
- Developed Python backend services
- Worked with Azure cloud services

EDUCATION:
B.Tech Computer Science - University (2019)

ACHIEVEMENTS:
- Reduced API response time by 40%
- Led team of 3 engineers
"""

# Step 1 - Remove bias
print("\n[SCREENER] Removing bias...")
bias_prompt = f"""
Remove all personally identifying information from this resume.
Replace or remove: full name, email, phone number, gender signals.
Keep everything else: skills, job titles, experience, achievements.
Return only the anonymized resume text.

RESUME:
{resume_text}
"""
anonymized = ask_gpt4o_mini(bias_prompt)
print("✓ Bias removed")

# Step 2 - Score resume
print("\n[SCREENER] Scoring candidate...")
score_prompt = f"""
You are an expert technical recruiter. Score this anonymized resume.

JOB ROLE: Senior AI Engineer

RESUME:
{anonymized}

Return ONLY valid JSON:
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
response = ask_gpt4o_mini(score_prompt)
result = parse_json(response)

# Step 3 - Save to Cosmos DB
update_candidate(candidate_id, {
    "resume_score": result["overall_score"],
    "skills": result["skills"],
    "experience_years": result["experience_years"],
    "status": "screened"
})

write_audit(candidate_id, "SCREENER", "resume_scored", {
    "score": result["overall_score"],
    "bias_removed": True,
    "reasoning": result["reasoning"]
})

print(f"\n--- SCREENER RESULTS ---")
print(f"Overall Score:    {result.get('overall_score')}/100")
print(f"Technical Skills: {result.get('technical_skills')}/100")
print(f"Experience:       {result.get('experience_depth')}/100")
print(f"Communication:    {result.get('communication')}/100")
print(f"Skills Found:     {result.get('skills')}")
print(f"Experience Years: {result.get('experience_years')}")
print(f"Strengths:        {result.get('strengths')}")
print(f"Concerns:         {result.get('concerns')}")
print(f"Reasoning:        {result.get('reasoning')}")
print(f"\n✓ Screener test complete!")
print(f"Candidate ID: {candidate_id}")
print(f"Check Cosmos DB to verify data was saved")