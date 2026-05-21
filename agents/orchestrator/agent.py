from shared.cosmos_client import save_candidate, get_candidate, update_candidate, write_audit
from shared.openai_client import ask_gpt4o, parse_json
from shared.config import config
from agents.screener.agent import run_screener
from agents.evaluator.agent import run_evaluator
from agents.communicator.agent import run_communicator
import uuid

HIRE_THRESHOLD    = 65
HUMAN_THRESHOLD   = 70

def create_candidate(name: str, email: str,
                     phone: str, applied_role: str,
                     expected_ctc: str) -> str:
    """Create a new candidate record in Cosmos DB."""
    candidate_id = str(uuid.uuid4())

    candidate = {
        "id":           candidate_id,
        "name":         name,
        "email":        email,
        "phone":        phone,
        "applied_role": applied_role,
        "expected_ctc": expected_ctc,
        "status":       "applied"
    }

    save_candidate(candidate)
    print(f"[ORCH] Candidate created: {candidate_id}")
    return candidate_id

def run_ai_pipeline(candidate_id: str,
                    pdf_bytes: bytes,
                    job_role: str) -> dict:
    """
    Run full AI pipeline for a candidate.
    Screener → Evaluator → Communicator
    All connected directly — no Service Bus needed.
    """
    print(f"[ORCH] Starting AI pipeline for: {candidate_id}")

    # Step 1 - Screen the resume
    print(f"[ORCH] Step 1: Screening resume...")
    screen_result = run_screener(candidate_id, pdf_bytes, job_role)

    if "error" in screen_result:
        print(f"[ORCH] Screener failed: {screen_result['error']}")
        return {"status": "failed", "reason": "screener_error"}

    resume_score = screen_result.get("overall_score", 0)
    print(f"[ORCH] Resume score: {resume_score}/100")

    # Step 2 - Check if candidate passes screening
    if resume_score < HIRE_THRESHOLD:
        print(f"[ORCH] Score too low. Sending rejection.")
        run_communicator(candidate_id, "REJECT")
        return {
            "status":       "rejected",
            "reason":       "low_resume_score",
            "resume_score": resume_score
        }

    # Step 3 - Check if candidate needs human interview
    if resume_score >= HUMAN_THRESHOLD:
        print(f"[ORCH] Strong candidate. Needs human interview.")
        update_candidate(candidate_id, {
            "status": "waiting_human_approval"
        })
        write_audit(candidate_id, "ORCHESTRATOR",
                    "human_interview_needed", {
            "resume_score": resume_score,
            "reason": "Score above human threshold"
        })
        return {
            "status":       "needs_human_interview",
            "resume_score": resume_score
        }

    # Step 4 - Run evaluator for borderline candidates
    print(f"[ORCH] Step 4: Running evaluator...")
    eval_result = run_evaluator(candidate_id)

    decision = eval_result.get("decision")
    print(f"[ORCH] Evaluator decision: {decision}")

    # Step 5 - Send communication
    print(f"[ORCH] Step 5: Sending communication...")
    if decision == "HIRE":
        run_communicator(candidate_id, "HIRE")
    else:
        run_communicator(candidate_id, "REJECT")

    write_audit(candidate_id, "ORCHESTRATOR",
                "pipeline_complete", {
        "decision":     decision,
        "resume_score": resume_score,
        "final_score":  eval_result.get("final_score")
    })

    print(f"[ORCH] Pipeline complete for: {candidate_id}")
    return {
        "status":      "complete",
        "decision":    decision,
        "final_score": eval_result.get("final_score")
    }

def resume_after_human_approval(candidate_id: str,
                                 human_tech_score: float,
                                 human_culture_score: float,
                                 human_notes: str,
                                 agreed_salary: str) -> dict:
    """
    Resume pipeline after human approves candidate.
    Called when HR clicks Approve in dashboard.
    """
    print(f"[ORCH] Resuming after human approval: {candidate_id}")

    # Update with human scores
    update_candidate(candidate_id, {
        "human_tech_score":    human_tech_score,
        "human_culture_score": human_culture_score,
        "human_notes":         human_notes,
        "agreed_salary":       agreed_salary,
        "status":              "evaluating"
    })

    # Run final evaluation
    eval_result = run_evaluator(candidate_id)
    decision    = eval_result.get("decision")

    # Send offer or rejection
    if decision == "HIRE":
        run_communicator(candidate_id, "HIRE")
    else:
        run_communicator(candidate_id, "REJECT")

    print(f"[ORCH] Post-human pipeline complete: {decision}")
    return {
        "status":      "complete",
        "decision":    decision,
        "final_score": eval_result.get("final_score")
    }