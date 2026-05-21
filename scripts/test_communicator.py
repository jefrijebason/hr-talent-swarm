import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.communicator.agent import run_communicator
from shared.cosmos_client import update_candidate

candidate_id = "d5e813dc-db64-43de-a7cd-4faf21ee5cb8"

# Update with a real email address to receive the test email
# Change this to YOUR real email address
update_candidate(candidate_id, {
    "name": "Arjun Mehta",
    "email": "jefrijebason@gmail.com",  # ← change this
    "applied_role": "Senior AI Engineer",
    "agreed_salary": "20 LPA",
    "decision_reasons": [
        "Strong Python and Azure skills",
        "Good system design experience",
        "Recommend hire"
    ]
})

print("Testing Communicator Agent — sending HIRE email...")
result = run_communicator(candidate_id, "HIRE")

print(f"\n--- COMMUNICATOR RESULTS ---")
print(f"Email sent: {result}")
print(f"Check your inbox!")