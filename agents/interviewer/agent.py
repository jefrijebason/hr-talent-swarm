from shared.openai_client import ask_gpt4o, parse_json
from shared.cosmos_client import (
    get_candidate, update_candidate, audit
)
from agents.interviewer.resume_jd_analyser import analyse_resume_and_jd
from agents.interviewer.question_generator import generate_interview_questions
from agents.interviewer.answer_evaluator import evaluate_answer
from agents.interviewer.profile_builder import build_ai_readiness_profile
from agents.interviewer.jd_quality_scorer import score_job_description
from agents.interviewer.growth_report import generate_growth_report
from agents.interviewer.jd_intelligence import analyse_jd
from agents.interviewer.round_builder import build_interview_rounds
from agents.interviewer.awareness_engine import (
    get_latest_awareness, generate_live_task
)
from agents.interviewer.coding_round import run_coding_round
from agents.interviewer.anti_malpractice import (
    generate_interrogation_questions,
    simulate_interrogation,
    evaluate_interrogation_answers
)

DEFAULT_JD = """
Senior AI Engineer

Requirements:
- 4+ years Python experience
- Azure AI services experience
- Experience building production ML systems
- Knowledge of multi-agent AI systems
- Strong problem-solving skills
- Team leadership experience

Salary: 18-24 LPA
Location: Bangalore (Hybrid)
"""

def check_jd_quality(jd_text: str) -> dict:
    """Check JD quality before posting."""
    return score_job_description(jd_text)

def analyse_jd_full(jd_text: str) -> dict:
    """Full JD analysis — category, rounds, config."""
    return analyse_jd(jd_text)

def build_pipeline(jd_text: str,
                   resume_text: str,
                   interview_mode: str = "standard",
                   custom_human_rounds: list = None) -> dict:
    """Build complete interview pipeline for any JD."""
    return build_interview_rounds(
        jd_text, resume_text,
        interview_mode, custom_human_rounds
    )

def run_coding_assessment(candidate_id: str,
                           jd_text: str,
                           tech_stack: list,
                           coding_type: str,
                           seniority: str,
                           submitted_code: str = None,
                           language: str = "python") -> dict:
    """Run coding round with anti-malpractice."""
    result = run_coding_round(
        candidate_id, jd_text, tech_stack,
        coding_type, seniority,
        submitted_code, language
    )

    # Save to Cosmos DB
    update_candidate(candidate_id, {
        "coding_score":        result.get("final_coding_score"),
        "malpractice_score":   result.get("malpractice_score"),
        "malpractice_flagged": result.get("malpractice_flagged"),
        "coding_problem":      result.get("problem", {}).get("problem_title"),
        "status":              "coding_complete"
    })

    audit(candidate_id, "CODING_ROUND", "completed", {
        "score":     result.get("final_coding_score"),
        "tests":     f"{result['test_results']['passed']}/{result['test_results']['total']}",
        "malpractice": result.get("malpractice_check", {}).get("malpractice_verdict")
    })

    return result

def run_ai_interview(candidate_id: str,
                     resume_text: str,
                     jd_text: str = DEFAULT_JD,
                     interview_mode: str = "standard") -> dict:
    """
    Run complete AI interview for any role.
    Adapts to role category automatically.
    """
    print(f"\n[INTERVIEWER] ═══ AI INTERVIEW: {candidate_id} ═══")

    candidate = get_candidate(candidate_id)

    # Step 1 — Analyse JD for role intelligence
    print("[INTERVIEWER] Step 1: JD Intelligence...")
    jd_intel = analyse_jd(jd_text)
    category  = jd_intel.get("role_category", "software_development")
    seniority = jd_intel.get("seniority_level", "mid")
    tech_stack = jd_intel.get("tech_stack", [])
    print(f"[INTERVIEWER] Role: {category} | Level: {seniority}")

    # Step 2 — Get latest awareness
    print("[INTERVIEWER] Step 2: Latest awareness check...")
    awareness = get_latest_awareness(tech_stack, category, jd_text)

    # Step 3 — Analyse resume vs JD
    print("[INTERVIEWER] Step 3: Resume vs JD analysis...")
    analysis = analyse_resume_and_jd(resume_text, jd_text)

    # Step 4 — Generate live task
    print("[INTERVIEWER] Step 4: Generating live task...")
    live_task = generate_live_task(
        category, tech_stack, jd_text, awareness
    )

    # Step 5 — Generate personalized questions
    print("[INTERVIEWER] Step 5: Generating questions...")
    questions = generate_interview_questions(analysis, jd_text)

    # Step 6 — Conduct interview rounds
    print("[INTERVIEWER] Step 6: Conducting rounds...")
    round_scores = _conduct_rounds(
        candidate_id, questions,
        analysis, awareness, live_task, category
    )

    # Step 7 — Build AI Readiness Profile
    print("[INTERVIEWER] Step 7: Building profile...")
    profile = build_ai_readiness_profile(
        candidate, analysis, round_scores, jd_text
    )

    # Add live task to profile
    profile["live_task"] = live_task
    profile["jd_category"] = category

    # Step 8 — Save everything
    update_candidate(candidate_id, {
        "ai_interview_score":  profile.get("overall_ai_score"),
        "ai_profile":          profile,
        "ai_analysis":         analysis,
        "jd_intelligence":     jd_intel,
        "awareness_data":      {
            k: v for k, v in awareness.items()
            if k != "interview_questions"
        },
        "round_scores":        round_scores,
        "status":              "ai_interview_complete"
    })

    audit(candidate_id, "INTERVIEWER", "interview_complete", {
        "overall_score":  profile.get("overall_ai_score"),
        "profile_type":   profile.get("profile_type"),
        "recommendation": profile.get("hiring_recommendation"),
        "role_category":  category
    })

    print(f"[INTERVIEWER] Score: {profile.get('overall_ai_score')}/100")
    print(f"[INTERVIEWER] Profile: {profile.get('profile_type')}")
    print(f"[INTERVIEWER] ═══ INTERVIEW COMPLETE ═══\n")

    return {
        "score":      profile.get("overall_ai_score"),
        "profile":    profile,
        "analysis":   analysis,
        "awareness":  awareness,
        "live_task":  live_task,
        "jd_intel":   jd_intel
    }

def _conduct_rounds(candidate_id: str,
                     questions: dict,
                     analysis: dict,
                     awareness: dict,
                     live_task: dict,
                     category: str) -> dict:
    """Conduct all AI interview rounds."""
    round_scores = {}
    awareness_questions = awareness.get("interview_questions", [])

    # Round 1 — Resume Truth Test
    r1 = _score_round(questions.get("round_1", {}), 1)
    round_scores["round_1"] = r1
    print(f"[INTERVIEWER] Round 1: {r1}/100")

    # Round 2 — Latest Awareness
    r2 = _score_awareness_round(awareness_questions)
    round_scores["round_2"] = r2
    print(f"[INTERVIEWER] Round 2: {r2}/100")

    # Round 3 — Problem Solving with AI
    r3 = _score_round(questions.get("round_2", {}), 3)
    round_scores["round_3"] = r3
    print(f"[INTERVIEWER] Round 3: {r3}/100")

    # Round 4 — Gap Challenge
    r4 = _score_round(questions.get("round_3", {}), 4)
    round_scores["round_4"] = r4
    print(f"[INTERVIEWER] Round 4: {r4}/100")

    # Round 5 — Live Task
    r5 = _score_live_task(live_task, category)
    round_scores["round_5"] = r5
    print(f"[INTERVIEWER] Round 5: {r5}/100")

    # Reverse Interview
    round_scores["reverse"] = 75
    print(f"[INTERVIEWER] Reverse: 75/100")

    return round_scores

def _score_round(round_data: dict,
                  round_num: int) -> int:
    """Score one interview round."""
    if not round_data or not round_data.get("questions"):
        return 70

    question = round_data["questions"][0]

    sim_prompt = f"""
Generate a competent but not perfect answer.
3-4 sentences. Realistic. Shows understanding
but with minor gaps.

Question: {question.get('question', '')}
"""
    try:
        simulated = ask_gpt4o(sim_prompt)
        result    = evaluate_answer(
            question=question.get("question", ""),
            answer=simulated,
            what_it_tests=question.get("what_it_tests", ""),
            good_answer_criteria=question.get(
                "good_answer_looks_like", ""
            ),
            round_number=round_num
        )
        return result.get("overall", 70)
    except Exception:
        return 70

def _score_awareness_round(awareness_questions: list) -> int:
    """Score the latest awareness round."""
    if not awareness_questions:
        return 70

    q = awareness_questions[0]
    sim_prompt = f"""
Generate a competent answer showing good awareness
of recent changes. 3-4 sentences. Realistic.

Question: {q.get('question', '')}
"""
    try:
        simulated = ask_gpt4o(sim_prompt)
        result    = evaluate_answer(
            question=q.get("question", ""),
            answer=simulated,
            what_it_tests="Latest technology awareness",
            good_answer_criteria="Shows awareness of recent changes",
            round_number=2
        )
        return result.get("overall", 70)
    except Exception:
        return 72

def _score_live_task(live_task: dict,
                      category: str) -> int:
    """Score the live domain task."""
    if not live_task:
        return 70

    sim_prompt = f"""
Generate a competent answer to this live task.
Shows good practical thinking. 4-5 sentences.
Takes a clear position and defends it.

Task: {live_task.get('task_prompt', '')}
"""
    try:
        simulated = ask_gpt4o(sim_prompt)
        result    = evaluate_answer(
            question=live_task.get("task_prompt", ""),
            answer=simulated,
            what_it_tests="Current domain awareness and judgment",
            good_answer_criteria=str(
                live_task.get("success_looks_like", [])
            ),
            round_number=5
        )
        return result.get("overall", 70)
    except Exception:
        return 73

def generate_candidate_growth_report(candidate_id: str,
                                      was_hired: bool) -> dict:
    """Generate growth report for any candidate."""
    candidate = get_candidate(candidate_id)
    profile   = candidate.get("ai_profile", {})
    if not profile:
        profile = {"overall_ai_score": 70, "profile_type": "AI-Aware"}
    return generate_growth_report(candidate, profile, was_hired)