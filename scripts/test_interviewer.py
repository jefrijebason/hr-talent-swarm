import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.interviewer.agent import run_ai_interview, check_jd_quality
from shared.cosmos_client import get_candidate

candidate_id = "a7af4c66-27df-4aa4-b3a7-d683811a0af6"

# Test resume text
resume_text = """
Arjun Mehta - Senior AI Engineer

SKILLS:
Python 6 years, Azure ML, Azure OpenAI,
FastAPI, Docker, Kubernetes, PostgreSQL,
Machine Learning, NLP, REST APIs, Git

EXPERIENCE:
Senior AI Engineer - Tech Company (2022-2026)
Built ML pipelines processing 1M records daily
Deployed GPT-4 powered applications on Azure
Led team of 5 engineers
Reduced model inference time by 60 percent

AI Engineer - Startup (2020-2022)
Built NLP models for text classification
Deployed models using Docker and Kubernetes

EDUCATION:
M.Tech Artificial Intelligence (2020)

ACHIEVEMENTS:
Azure AI Engineer certification
Published 2 research papers on NLP
Reduced hiring costs by 40 percent using AI
"""

# Test 1 - JD Quality Check
print("=" * 50)
print("TEST 1: JD Quality Scorer")
print("=" * 50)

test_jd = """
We need a rockstar Python developer with 10+ years
of experience. Must know every framework ever created.
Must be available 24/7. Must have worked at FAANG.
No salary range provided. 25 requirements listed.
"""

jd_result = check_jd_quality(test_jd)
print(f"JD Quality: {jd_result.get('overall_quality')}/10")
print(f"Issues found: {len(jd_result.get('issues', []))}")
for issue in jd_result.get('issues', [])[:3]:
    print(f"  ❌ {issue.get('type')}: {issue.get('problem')}")

# Test 2 - Full AI Interview
print("\n" + "=" * 50)
print("TEST 2: Full AI Interview")
print("=" * 50)

result = run_ai_interview(candidate_id, resume_text)

print(f"\n--- AI INTERVIEW RESULTS ---")
print(f"Overall Score:    {result.get('score')}/100")
profile = result.get('profile', {})
print(f"Profile Type:     {profile.get('profile_type')}")
print(f"Percentile:       {profile.get('percentile')}")
print(f"Recommendation:   {profile.get('hiring_recommendation')}")

dims = profile.get('dimension_scores', {})
print(f"\nDimension Scores:")
for dim, score in dims.items():
    print(f"  {dim}: {score}/100")

briefing = profile.get('human_interview_briefing', {})
print(f"\nHuman Interview Briefing:")
print(f"Focus on: {briefing.get('focus_on', [])}")
print(f"Suggested questions: {briefing.get('suggested_questions', [])[:2]}")

market = profile.get('market_intelligence', {})
print(f"\nMarket Intelligence:")
print(f"Expected: {market.get('candidate_expected')}")
print(f"Market rate: {market.get('market_rate')}")
print(f"Recommendation: {market.get('recommendation')}")