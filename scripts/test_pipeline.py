import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator.agent import create_candidate, run_ai_pipeline

# Test resume text as bytes
test_resume = """
Arjun Mehta
Senior AI Engineer with 6 years experience

SKILLS:
Python, Azure AI, Azure ML, GPT-4, LangChain,
FastAPI, Docker, Kubernetes, PostgreSQL,
Machine Learning, Deep Learning, NLP,
REST APIs, Git, CI/CD, Terraform

EXPERIENCE:
Senior AI Engineer - Microsoft Partner Company (2022-2026)
- Built production ML pipelines processing 1M records daily
- Deployed GPT-4 powered applications on Azure OpenAI
- Led team of 5 engineers building AI solutions
- Reduced model inference time by 60 percent

AI Engineer - Tech Startup (2020-2022)
- Built NLP models for text classification
- Deployed models using Docker and Kubernetes
- Developed FastAPI backends for ML models

Software Engineer - IT Company (2018-2020)
- Python development and REST APIs
- Azure cloud services integration

EDUCATION:
M.Tech Artificial Intelligence - IIT (2018)
B.Tech Computer Science - NIT (2016)

ACHIEVEMENTS:
- Published 2 research papers on NLP
- Azure AI Engineer certification
- Led successful migration of ML platform to Azure
- Reduced hiring costs by 40 percent using AI automation
""".encode("utf-8")

# Step 1 - Create candidate
print("Creating candidate...")
candidate_id = create_candidate(
    name="Arjun Mehta",
    email="jefrijebason@gmail.com",
    phone="9876543210",
    applied_role="Senior AI Engineer",
    expected_ctc="20 LPA"
)
print(f"Candidate ID: {candidate_id}")

# Step 2 - Run full AI pipeline
print("\nRunning full AI pipeline...")
result = run_ai_pipeline(candidate_id, test_resume, "Senior AI Engineer")

print(f"\n--- PIPELINE RESULTS ---")
print(f"Status:      {result.get('status')}")
print(f"Decision:    {result.get('decision', 'N/A')}")
print(f"Final Score: {result.get('final_score', 'N/A')}")
print(f"Reason:      {result.get('reason', 'N/A')}")
print(f"\nCheck your email inbox!")