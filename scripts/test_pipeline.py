import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator.agent import create_candidate, run_ai_pipeline
from agents.interviewer.agent import run_ai_interview, check_jd_quality
from shared.cosmos_client import get_candidate

# ─────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────

JD_TEXT = """
Senior AI Engineer

We are looking for a Senior AI Engineer
to join our AI Platform team.

Requirements:
- 4+ years Python experience
- Azure AI services experience
- Experience building production ML systems
- Knowledge of multi-agent AI systems
- Strong problem-solving skills
- Team leadership experience

Responsibilities:
- Design and build AI agent systems
- Deploy ML models to production
- Lead a team of 3-4 engineers
- Collaborate with product team

Salary: 18-24 LPA
Location: Bangalore (Hybrid)
"""

RESUME_TEXT = """
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

# ─────────────────────────────────────
# TEST 1 — JD QUALITY CHECK
# ─────────────────────────────────────
print("=" * 55)
print("TEST 1: JD Quality Scorer")
print("=" * 55)

bad_jd = """
We need a rockstar Python developer with 10 years
experience. Must know every framework. Must be
available 24/7. Must have worked at FAANG.
No salary provided. 25 requirements listed.
"""

from agents.interviewer.jd_quality_scorer import score_job_description
jd_result = score_job_description(bad_jd)

print(f"Quality Score:  {jd_result.get('overall_quality')}/10")
print(f"Issues Found:   {len(jd_result.get('issues', []))}")
for issue in jd_result.get('issues', [])[:3]:
    print(f"  ❌ {issue.get('type')}: {issue.get('problem')}")
print(f"Impact:         {jd_result.get('statistics', {}).get('estimated_application_impact')}")

# ─────────────────────────────────────
# TEST 2 — CREATE CANDIDATE
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 2: Create Candidate")
print("=" * 55)

candidate_id = create_candidate(
    name="Arjun Mehta",
    email="jefrijebason@gmail.com",
    phone="9876543210",
    applied_role="Senior AI Engineer",
    expected_ctc="20 LPA"
)
print(f"Candidate ID: {candidate_id}")

# ─────────────────────────────────────
# TEST 3 — RESUME SCREENING
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 3: Resume Screening")
print("=" * 55)

from agents.screener.agent import run_screener
screen_result = run_screener(
    candidate_id,
    RESUME_TEXT.encode("utf-8"),
    "Senior AI Engineer"
)
print(f"Resume Score:   {screen_result.get('overall_score')}/100")
print(f"Skills Found:   {screen_result.get('skills')}")
print(f"Experience:     {screen_result.get('experience_years')} years")

# ─────────────────────────────────────
# TEST 4 — AI INTERVIEW
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 4: AI Interview (4 Rounds)")
print("=" * 55)

interview_result = run_ai_interview(
    candidate_id,
    RESUME_TEXT,
    JD_TEXT
)

profile = interview_result.get('profile', {})
dims    = profile.get('dimension_scores', {})
market  = profile.get('market_intelligence', {})
briefing = profile.get('human_interview_briefing', {})

print(f"AI Score:       {interview_result.get('score')}/100")
print(f"Profile Type:   {profile.get('profile_type')}")
print(f"Percentile:     {profile.get('percentile')}")
print(f"Recommendation: {profile.get('hiring_recommendation')}")

print(f"\nDimension Scores:")
for dim, score in dims.items():
    bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
    print(f"  {dim:<25} {bar} {score}/100")

print(f"\nMarket Intelligence:")
print(f"  Expected:    {market.get('candidate_expected')}")
print(f"  Market Rate: {market.get('market_rate')}")
print(f"  Suggest:     {market.get('recommendation')}")
print(f"  Risk:        {market.get('retention_risk')}")

print(f"\nHuman Interview Briefing:")
print(f"  Do NOT re-test: {briefing.get('do_not_test_again', [])}")
print(f"  Focus on:       {briefing.get('focus_on', [])}")
print(f"  Watch for:      {briefing.get('watch_out_for', [])}")

# ─────────────────────────────────────
# TEST 5 — EVALUATOR
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 5: Evaluator Agent")
print("=" * 55)

from agents.evaluator.agent import run_evaluator
eval_result = run_evaluator(candidate_id)

print(f"Final Score:    {eval_result.get('final_score')}/100")
print(f"Decision:       {eval_result.get('decision')}")
print(f"Confidence:     {eval_result.get('confidence')}%")
print(f"Bar Raised:     {eval_result.get('bar_raised')}")

# ─────────────────────────────────────
# TEST 6 — COMMUNICATOR
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 6: Communicator — Sending Email")
print("=" * 55)

from agents.communicator.agent import run_communicator
decision = eval_result.get('decision', 'NO_HIRE')
action   = "HIRE" if decision == "HIRE" else "REJECT"

comm_result = run_communicator(candidate_id, action)
print(f"Email Sent:     {comm_result}")
print(f"Action:         {action}")
print(f"Check inbox:    jefrijebason@gmail.com")

# ─────────────────────────────────────
# TEST 7 — GROWTH REPORT
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("TEST 7: Candidate Growth Report")
print("=" * 55)

from agents.interviewer.agent import generate_candidate_growth_report
growth = generate_candidate_growth_report(
    candidate_id,
    was_hired=(action == "HIRE")
)
print(f"Subject:        {growth.get('subject')}")
print(f"Key Insights:   {growth.get('key_insights', [])}")

# ─────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("PIPELINE SUMMARY")
print("=" * 55)

final_candidate = get_candidate(candidate_id)
print(f"Candidate:      {final_candidate.get('name')}")
print(f"Resume Score:   {final_candidate.get('resume_score')}/100")
print(f"AI Interview:   {final_candidate.get('ai_interview_score')}/100")
print(f"Final Score:    {final_candidate.get('final_score')}/100")
print(f"Decision:       {final_candidate.get('decision')}")
print(f"Status:         {final_candidate.get('status')}")
print(f"Candidate ID:   {candidate_id}")
print(f"\n✓ Full pipeline test complete!")