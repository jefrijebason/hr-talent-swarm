import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator.agent import (
    technical_interview_result,
    hr_interview_result
)

# Use candidate from last pipeline test
candidate_id = "c3d872a1-758f-47f4-ad20-a50335ec5a0c"

print("=" * 55)
print("TEST: Gate 1 — Technical Interview Result")
print("=" * 55)

# Simulate Technical Lead clicking PASS
tech_result = technical_interview_result(
    candidate_id=candidate_id,
    tech_score=8.0,
    system_design_score=7.5,
    notes="Strong Python and Azure knowledge. Good system design thinking. Minor gaps in agent architecture but learns fast.",
    passed=True
)

print(f"Status:    {tech_result.get('status')}")
print(f"Briefing:  {tech_result.get('hr_briefing', {}).get('focus_on')}")

print("\n" + "=" * 55)
print("TEST: Gate 2 — HR Interview Result")
print("=" * 55)

# Simulate HR Manager clicking HIRE
hr_result = hr_interview_result(
    candidate_id=candidate_id,
    culture_score=8.0,
    communication_score=7.5,
    agreed_salary="21 LPA",
    notes="Great cultural fit. Motivated by impact. Good communicator. Recommend hire.",
    hired=True
)

print(f"Status:      {hr_result.get('status')}")
print(f"Decision:    {hr_result.get('decision')}")
print(f"Final Score: {hr_result.get('final_score')}")
print(f"\nCheck inbox: jefrijebason@gmail.com")