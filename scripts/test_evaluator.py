import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.evaluator.agent import run_evaluator

# Use the candidate ID from the screener test
candidate_id = "d5e813dc-db64-43de-a7cd-4faf21ee5cb8"

print("Running Evaluator Agent...")
result = run_evaluator(candidate_id)

print(f"\n--- EVALUATOR RESULTS ---")
print(f"Decision:    {result.get('decision')}")
print(f"Final Score: {result.get('final_score')}/100")
print(f"Confidence:  {result.get('confidence')}%")
print(f"Bar Raised:  {result.get('bar_raised')}")
print(f"Reasons:     {result.get('reasons')}")
print(f"Feedback:    {result.get('feedback_for_candidate')}")