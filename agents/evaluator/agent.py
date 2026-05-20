from shared.openai_client import ask_gpt4o, parse_json
from shared.cosmos_client import get_candidate, update_candidate, write_audit

# Scoring weights
WEIGHTS = {
    "resume_score":        0.20,
    "coding_score":        0.25,
    "ai_interview_score":  0.15,
    "human_tech_score":    0.25,
    "human_culture_score": 0.15
}

HIRE_THRESHOLD = 65

def calculate_weighted_score(candidate: dict) -> float:
    """Calculate final weighted score from all agent scores."""
    total_score  = 0
    total_weight = 0

    for field, weight in WEIGHTS.items():
        value = candidate.get(field)
        if value is not None:
            # Human scores are out of 10 — convert to 100
            if field in ["human_tech_score", "human_culture_score"]:
                value = value * 10
            total_score  += value * weight
            total_weight += weight

    if total_weight == 0:
        return 0

    return round(total_score / total_weight, 1)

def detect_conflict(candidate: dict) -> bool:
    """Check if AI scores and human scores disagree significantly."""
    ai_scores = []
    human_scores = []

    if candidate.get("resume_score"):
        ai_scores.append(candidate["resume_score"])
    if candidate.get("ai_interview_score"):
        ai_scores.append(candidate["ai_interview_score"])
    if candidate.get("human_tech_score"):
        human_scores.append(candidate["human_tech_score"] * 10)
    if candidate.get("human_culture_score"):
        human_scores.append(candidate["human_culture_score"] * 10)

    if not ai_scores or not human_scores:
        return False

    ai_avg    = sum(ai_scores) / len(ai_scores)
    human_avg = sum(human_scores) / len(human_scores)

    return abs(ai_avg - human_avg) > 30

def run_evaluator(candidate_id: str) -> dict:
    """
    Main evaluator function.
    1. Get all scores from Cosmos DB
    2. Calculate weighted score
    3. Check for conflicts
    4. Make hire/no-hire decision
    5. Save to Cosmos DB
    """
    print(f"[EVALUATOR] Starting for candidate: {candidate_id}")

    # Get candidate from database
    candidate = get_candidate(candidate_id)

    # Calculate weighted score
    final_score = calculate_weighted_score(candidate)
    print(f"[EVALUATOR] Weighted score: {final_score}/100")

    # Check for conflicts
    conflict = detect_conflict(candidate)
    if conflict:
        print(f"[EVALUATOR] Conflict detected between AI and human scores")

    # Make decision using GPT-4o
    prompt = f"""
You are the final hiring decision maker — the Bar Raiser.
Make a hiring decision based on these scores:

Resume Score:        {candidate.get('resume_score', 'N/A')}
Coding Score:        {candidate.get('coding_score', 'N/A')}
AI Interview Score:  {candidate.get('ai_interview_score', 'N/A')}
Human Tech Score:    {candidate.get('human_tech_score', 'N/A')} /10
Human Culture Score: {candidate.get('human_culture_score', 'N/A')} /10
Human Notes:         {candidate.get('human_notes', 'None')}
Agreed Salary:       {candidate.get('agreed_salary', 'Not confirmed')}
Final Weighted Score: {final_score}/100
Conflict Detected:   {conflict}

Hire threshold is 65/100.

Return ONLY valid JSON:
{{
    "decision": "HIRE" or "NO_HIRE",
    "confidence": 0-100,
    "bar_raised": true or false,
    "reasons": ["reason1", "reason2", "reason3"],
    "feedback_for_candidate": "constructive 2 sentence feedback"
}}
"""

    response  = ask_gpt4o(prompt)
    result    = parse_json(response)

    # Add final score to result
    result["final_score"] = final_score
    result["conflict"]    = conflict

    # Determine status
    status = "offer_sent" if result["decision"] == "HIRE" else "rejected"

    # Save to Cosmos DB
    update_candidate(candidate_id, {
        "final_score":      final_score,
        "confidence":       result["confidence"],
        "decision":         result["decision"],
        "decision_reasons": result["reasons"],
        "status":           status
    })

    write_audit(candidate_id, "EVALUATOR", "decision_made", {
        "decision":   result["decision"],
        "score":      final_score,
        "confidence": result["confidence"],
        "conflict":   conflict
    })

    print(f"[EVALUATOR] Decision: {result['decision']} | Score: {final_score} | Confidence: {result['confidence']}%")
    return result