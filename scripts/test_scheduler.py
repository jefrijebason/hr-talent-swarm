import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.scheduler.agent import run_scheduler

candidate_id = "c3d872a1-758f-47f4-ad20-a50335ec5a0c"

print("=" * 55)
print("TEST 1: Schedule Technical Interview")
print("=" * 55)

result = run_scheduler(candidate_id, "technical")

print(f"Slot:        {result.get('slot_human')}")
print(f"Meeting URL: {result.get('meeting_url')}")
print(f"Attendees:   {result.get('attendees')}")

print("\n" + "=" * 55)
print("TEST 2: Schedule HR Interview")
print("=" * 55)

result2 = run_scheduler(candidate_id, "hr")

print(f"Slot:        {result2.get('slot_human')}")
print(f"Meeting URL: {result2.get('meeting_url')}")
print(f"Attendees:   {result2.get('attendees')}")

print("\nCheck inbox for interview invite emails!")