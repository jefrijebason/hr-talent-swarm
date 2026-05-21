from shared.openai_client import ask_gpt4o, parse_json

def evaluate_answer(question: str,
                    answer: str,
                    what_it_tests: str,
                    good_answer_criteria: str,
                    round_number: int) -> dict:
    """
    Evaluate a single answer from the candidate.
    Returns detailed score with reasoning.
    """

    prompt = f"""
You are evaluating a candidate answer in an AI-native interview.
Be honest and precise. Not too harsh, not too lenient.

ROUND: {round_number}
QUESTION: {question}
WHAT THIS TESTS: {what_it_tests}
GOOD ANSWER CRITERIA: {good_answer_criteria}

CANDIDATE ANSWER:
{answer}

Evaluate on these dimensions (0-100 each):
- technical_accuracy: Is the technical content correct?
- depth: How deep is their understanding?
- ai_thinking: Did they think about how AI can help?
- communication: How clearly did they explain?
- overall: Weighted final score

Return ONLY valid JSON:
{{
    "technical_accuracy": 0-100,
    "depth": 0-100,
    "ai_thinking": 0-100,
    "communication": 0-100,
    "overall": 0-100,
    "strengths": ["what was good"],
    "weaknesses": ["what was missing"],
    "verdict": "Strong/Acceptable/Weak",
    "follow_up_needed": true or false,
    "reasoning": "2 sentence honest evaluation"
}}
"""

    response = ask_gpt4o(prompt)
    return parse_json(response)

def evaluate_prompt(candidate_prompt: str,
                    test_data: str,
                    success_criteria: list,
                    openai_client) -> dict:
    """
    Actually run the candidate's prompt on test data.
    Score based on real output quality.
    """
    print("[EVALUATOR] Running candidate prompt on real data...")

    try:
        # Run their actual prompt
        result = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user",
                 "content": f"{candidate_prompt}\n\nDATA:\n{test_data}"}
            ],
            temperature=0.1
        )
        actual_output = result.choices[0].message.content

        # Now evaluate the output
        eval_prompt = f"""
Evaluate this AI prompt output against the success criteria.

CANDIDATE'S PROMPT:
{candidate_prompt}

TEST DATA USED:
{test_data}

ACTUAL OUTPUT PRODUCED:
{actual_output}

SUCCESS CRITERIA:
{success_criteria}

Return ONLY valid JSON:
{{
    "criteria_met": [
        {{"criterion": "criterion text", "met": true/false, "reason": "why"}}
    ],
    "output_quality": 0-100,
    "prompt_clarity": 0-100,
    "reliability": 0-100,
    "overall_score": 0-100,
    "what_worked": "what was good about the prompt",
    "what_failed": "what the prompt missed",
    "improved_version_hint": "one tip to improve"
}}
"""
        eval_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1
        )
        return parse_json(eval_response.choices[0].message.content)

    except Exception as e:
        print(f"[EVALUATOR] Prompt execution error: {e}")
        return {
            "overall_score": 0,
            "output_quality": 0,
            "prompt_clarity": 0,
            "reliability": 0,
            "what_failed": str(e)
        }