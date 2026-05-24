from shared.openai_client import ask_gpt4o, parse_json

def generate_interrogation_questions(submission: str,
                                      submission_type: str,
                                      role_category: str) -> list:
    """
    Generate 5 targeted questions about the
    candidate's own submission.
    Works for code, SQL, designs, case studies,
    campaign plans, architecture diagrams.
    """
    print(f"[MALPRACTICE] Generating interrogation for {submission_type}...")

    prompt = f"""
You are reviewing a candidate's submission for a
{role_category} role. Your job is to generate
5 targeted questions that test whether they
genuinely understand their own work.

SUBMISSION TYPE: {submission_type}

SUBMISSION:
{submission[:2000]}

Generate 5 questions that:
1. Reference specific parts of their submission
2. Are impossible to answer without truly understanding the work
3. Progress from surface to deep understanding
4. Test decision-making reasoning not just outcomes
5. Include at least one "what if" extension question

Question types to include:
- Line/section level: "On line X you did Y. Why?"
- Decision level: "You chose A over B. Defend that."
- Complexity level: "What is the complexity/tradeoff?"
- Alternative level: "Show me a different approach"
- Extension level: "How does this scale to 10x?"

Return ONLY valid JSON:
{{
    "submission_summary": "2 sentence summary of what they submitted",
    "questions": [
        {{
            "question_number": 1,
            "question": "specific question referencing their work",
            "what_it_tests": "what understanding this reveals",
            "strong_answer": "what a genuine author would say",
            "red_flag_answer": "what a copier would say",
            "follow_up": "deeper follow-up if they answer well"
        }},
        {{
            "question_number": 2,
            "question": "second specific question",
            "what_it_tests": "what this reveals",
            "strong_answer": "genuine author response",
            "red_flag_answer": "copier response",
            "follow_up": "deeper follow-up"
        }},
        {{
            "question_number": 3,
            "question": "third specific question",
            "what_it_tests": "what this reveals",
            "strong_answer": "genuine author response",
            "red_flag_answer": "copier response",
            "follow_up": "deeper follow-up"
        }},
        {{
            "question_number": 4,
            "question": "show alternative approach",
            "what_it_tests": "flexibility and understanding",
            "strong_answer": "genuine author response",
            "red_flag_answer": "copier response",
            "follow_up": "deeper follow-up"
        }},
        {{
            "question_number": 5,
            "question": "extension to real scale or scenario",
            "what_it_tests": "engineering judgment",
            "strong_answer": "genuine author response",
            "red_flag_answer": "copier response",
            "follow_up": "deeper follow-up"
        }}
    ]
}}
"""

    try:
        response = ask_gpt4o(prompt)
        result   = parse_json(response)
        print(f"[MALPRACTICE] Generated {len(result.get('questions', []))} questions")
        return result.get("questions", [])
    except Exception as e:
        print(f"[MALPRACTICE] Error: {e}")
        return _fallback_questions(submission_type)

def evaluate_interrogation_answers(questions: list,
                                    answers: list,
                                    submission: str,
                                    submission_type: str) -> dict:
    """
    Score the candidate's answers to malpractice
    interrogation questions.
    Returns malpractice score and verdict.
    """
    print("[MALPRACTICE] Evaluating interrogation answers...")

    qa_pairs = []
    for i, q in enumerate(questions):
        answer = answers[i] if i < len(answers) else "No answer provided"
        qa_pairs.append({
            "question":      q.get("question"),
            "answer":        answer,
            "strong_answer": q.get("strong_answer"),
            "red_flag":      q.get("red_flag_answer")
        })

    prompt = f"""
Evaluate whether this candidate genuinely understands
their own {submission_type} submission.

ORIGINAL SUBMISSION:
{submission[:1500]}

QUESTION AND ANSWER PAIRS:
{qa_pairs}

For each answer evaluate:
- Does it show genuine understanding?
- Does it reference specifics from their submission?
- Are they explaining decisions or just describing output?
- Do they know WHY they made each choice?

Return ONLY valid JSON:
{{
    "per_question_scores": [
        {{
            "question_number": 1,
            "score": 0-100,
            "verdict": "Genuine/Uncertain/Suspicious",
            "reasoning": "why"
        }}
    ],
    "overall_score": 0-100,
    "malpractice_verdict": "Genuine/Possible Malpractice/Likely Malpractice",
    "confidence": 0-100,
    "red_flags": ["specific concern if any"],
    "summary": "2 sentence honest assessment",
    "recommendation": "Proceed/Flag for Human Review/Strong Flag"
}}
"""

    try:
        response = ask_gpt4o(prompt)
        result   = parse_json(response)

        score   = result.get("overall_score", 50)
        verdict = result.get("malpractice_verdict", "Uncertain")
        print(f"[MALPRACTICE] Score: {score}/100 | Verdict: {verdict}")
        return result

    except Exception as e:
        print(f"[MALPRACTICE] Evaluation error: {e}")
        return {
            "overall_score":       50,
            "malpractice_verdict": "Uncertain",
            "confidence":          0,
            "recommendation":      "Flag for Human Review"
        }

def simulate_interrogation(questions: list,
                             submission: str,
                             submission_type: str) -> list:
    """
    For testing — simulate candidate answers.
    In production candidate types real answers.
    """
    simulated_answers = []

    for q in questions:
        prompt = f"""
Simulate a competent but not perfect candidate answer
to this question about their own {submission_type}.
Make it realistic — 2-3 sentences. Natural language.

Original submission context:
{submission[:500]}

Question: {q.get('question')}
"""
        try:
            answer = ask_gpt4o(prompt)
            simulated_answers.append(answer.strip())
        except Exception:
            simulated_answers.append(
                "I made this choice because it seemed the most straightforward approach."
            )

    return simulated_answers

def _fallback_questions(submission_type: str) -> list:
    """Fallback questions if generation fails."""
    return [
        {
            "question_number": 1,
            "question": f"Walk me through your overall approach to this {submission_type}.",
            "what_it_tests": "High level understanding",
            "strong_answer": "Detailed explanation of thinking",
            "red_flag_answer": "Vague or generic response",
            "follow_up": "What alternatives did you consider?"
        },
        {
            "question_number": 2,
            "question": "What was the hardest decision you made here?",
            "what_it_tests": "Decision awareness",
            "strong_answer": "Specific tradeoff explained",
            "red_flag_answer": "Cannot identify any decision",
            "follow_up": "Why did you go that way?"
        },
        {
            "question_number": 3,
            "question": "What would you change if you had more time?",
            "what_it_tests": "Self-awareness of limitations",
            "strong_answer": "Specific improvements identified",
            "red_flag_answer": "Says nothing to improve",
            "follow_up": "How would that change affect the outcome?"
        },
        {
            "question_number": 4,
            "question": "Show me a completely different approach.",
            "what_it_tests": "Understanding of alternatives",
            "strong_answer": "Valid alternative explained",
            "red_flag_answer": "Cannot think of alternative",
            "follow_up": "What are the tradeoffs?"
        },
        {
            "question_number": 5,
            "question": "How does this work at 100x the scale?",
            "what_it_tests": "Scalability thinking",
            "strong_answer": "Specific bottlenecks identified",
            "red_flag_answer": "Says it just works",
            "follow_up": "What breaks first?"
        }
    ]