from shared.openai_client import ask_gpt4o, parse_json, client
from shared.cosmos_client import get_candidate, update_candidate, write_audit
from agents.interviewer.resume_jd_analyser import analyse_resume_and_jd
from agents.interviewer.question_generator import generate_interview_questions
from agents.interviewer.answer_evaluator import evaluate_answer, evaluate_prompt
from agents.interviewer.profile_builder import build_ai_readiness_profile
from agents.interviewer.jd_quality_scorer import score_job_description
from agents.interviewer.growth_report import generate_growth_report
import json

# Default job description for testing
DEFAULT_JD = """
Senior AI Engineer

We are looking for a Senior AI Engineer to join our AI Platform team.

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

Salary: ₹18-24 LPA
Location: Bangalore (Hybrid)
"""

def check_jd_quality(jd_text: str) -> dict:
    """Check JD quality before posting."""
    return score_job_description(jd_text)

def run_ai_interview(candidate_id: str,
                     resume_text: str,
                     jd_text: str = DEFAULT_JD) -> dict:
    """
    Run the complete AI interview for a candidate.
    Returns scores and AI Readiness Profile.
    """
    print(f"[INTERVIEWER] Starting AI interview for: {candidate_id}")

    candidate = get_candidate(candidate_id)

    # Step 1 — Analyse resume vs JD
    print("[INTERVIEWER] Step 1: Analysing resume vs JD...")
    analysis = analyse_resume_and_jd(resume_text, jd_text)

    # Step 2 — Generate personalized questions
    print("[INTERVIEWER] Step 2: Generating questions...")
    questions = generate_interview_questions(analysis, jd_text)

    # Step 3 — Conduct interview
    # In production this is interactive
    # For testing we simulate answers
    print("[INTERVIEWER] Step 3: Conducting interview...")
    round_scores = conduct_interview_rounds(
        candidate_id, questions, analysis
    )

    # Step 4 — Build AI Readiness Profile
    print("[INTERVIEWER] Step 4: Building profile...")
    profile = build_ai_readiness_profile(
        candidate, analysis, round_scores, jd_text
    )

    # Step 5 — Save everything to Cosmos DB
    update_candidate(candidate_id, {
        "ai_interview_score":  profile.get("overall_ai_score"),
        "ai_profile":          profile,
        "ai_analysis":         analysis,
        "interview_questions": questions,
        "round_scores":        round_scores,
        "status":              "ai_interview_complete"
    })

    write_audit(candidate_id, "INTERVIEWER", "interview_complete", {
        "overall_score":   profile.get("overall_ai_score"),
        "profile_type":    profile.get("profile_type"),
        "recommendation":  profile.get("hiring_recommendation")
    })

    print(f"[INTERVIEWER] Done. Score: {profile.get('overall_ai_score')}/100")
    return {
        "score":   profile.get("overall_ai_score"),
        "profile": profile,
        "analysis": analysis
    }

def conduct_interview_rounds(candidate_id: str,
                              questions: dict,
                              analysis: dict) -> dict:
    """
    Simulate interview rounds with auto-generated answers.
    In production — candidate types real answers.
    For testing — AI generates sample answers.
    """
    round_scores = {}

    # Round 1
    r1_score = simulate_and_score_round(
        questions.get("round_1", {}), 1
    )
    round_scores["round_1"] = r1_score
    print(f"[INTERVIEWER] Round 1 score: {r1_score}/100")

    # Round 2
    r2_score = simulate_and_score_round(
        questions.get("round_2", {}), 2
    )
    round_scores["round_2"] = r2_score
    print(f"[INTERVIEWER] Round 2 score: {r2_score}/100")

    # Round 3
    r3_score = simulate_and_score_round(
        questions.get("round_3", {}), 3
    )
    round_scores["round_3"] = r3_score
    print(f"[INTERVIEWER] Round 3 score: {r3_score}/100")

    # Round 4
    r4_score = simulate_and_score_round(
        questions.get("round_4", {}), 4
    )
    round_scores["round_4"] = r4_score
    print(f"[INTERVIEWER] Round 4 score: {r4_score}/100")

    # Reverse interview
    round_scores["reverse"] = 75

    return round_scores

def simulate_and_score_round(round_data: dict,
                               round_num: int) -> int:
    """
    For testing: simulate a good candidate answer
    and score it. Returns score 0-100.
    """
    if not round_data or not round_data.get("questions"):
        return 70

    question = round_data["questions"][0]

    # Simulate a competent answer
    sim_prompt = f"""
Generate a competent but not perfect answer to this
interview question. Make it realistic — good but with
minor gaps. 3-4 sentences.

Question: {question.get('question', '')}
"""
    simulated_answer = ask_gpt4o(sim_prompt)

    # Score the answer
    score_result = evaluate_answer(
        question=question.get("question", ""),
        answer=simulated_answer,
        what_it_tests=question.get("what_it_tests", ""),
        good_answer_criteria=question.get(
            "good_answer_looks_like", ""
        ),
        round_number=round_num
    )

    return score_result.get("overall", 70)

def generate_candidate_growth_report(candidate_id: str,
                                      was_hired: bool) -> dict:
    """Generate growth report for any candidate."""
    candidate = get_candidate(candidate_id)
    profile = candidate.get("ai_profile", {})
    return generate_growth_report(candidate, profile, was_hired)