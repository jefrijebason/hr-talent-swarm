from shared.openai_client import ask_gpt4o, parse_json

def generate_interview_questions(analysis: dict,
                                  jd_text: str) -> dict:
    """
    Generate 4 rounds of personalized questions
    based on resume vs JD analysis.
    Every question references something real
    from the candidate's actual experience.
    """
    print("[QUESTION GEN] Generating personalized questions...")

    prompt = f"""
You are conducting a world-class AI-native interview.
You have deeply analysed this candidate's profile.

CANDIDATE ANALYSIS:
{analysis}

JOB DESCRIPTION:
{jd_text}

Generate exactly 4 rounds of interview questions.
Every question must reference something specific
from the candidate's actual resume.
Never ask generic questions.

Return ONLY valid JSON:
{{
    "round_1": {{
        "title": "Resume Truth Test",
        "duration": "15 minutes",
        "objective": "Verify their strongest claims",
        "questions": [
            {{
                "question": "specific question referencing their resume",
                "what_it_tests": "what this question reveals",
                "good_answer_looks_like": "what a strong answer includes",
                "follow_up": "follow up if answer is strong",
                "probe_if_weak": "probe question if answer is vague"
            }},
            {{
                "question": "second question",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "strong answer criteria",
                "follow_up": "follow up question",
                "probe_if_weak": "probe if weak"
            }}
        ]
    }},
    "round_2": {{
        "title": "Problem Solving with AI",
        "duration": "15 minutes",
        "objective": "Test if they use AI to multiply their output",
        "questions": [
            {{
                "question": "real problem from JD + their background",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "strong answer criteria",
                "follow_up": "follow up",
                "probe_if_weak": "probe"
            }},
            {{
                "question": "second problem",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "strong answer",
                "follow_up": "follow up",
                "probe_if_weak": "probe"
            }}
        ]
    }},
    "round_3": {{
        "title": "JD Gap Challenge",
        "duration": "15 minutes",
        "objective": "Test learning agility on their specific gaps",
        "gap_being_tested": "the specific gap from analysis",
        "questions": [
            {{
                "question": "gap specific learning question",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "strong answer",
                "follow_up": "follow up",
                "probe_if_weak": "probe"
            }},
            {{
                "question": "apply new concept to their experience",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "strong answer",
                "follow_up": "follow up",
                "probe_if_weak": "probe"
            }}
        ]
    }},
    "round_4": {{
        "title": "Live Prompt Engineering",
        "duration": "15 minutes",
        "objective": "Test real prompt engineering on JD requirements",
        "challenge": "specific prompt challenge based on JD",
        "test_data": "what their prompt will be tested on",
        "success_criteria": [
            "criterion 1",
            "criterion 2",
            "criterion 3"
        ],
        "questions": [
            {{
                "question": "live prompt engineering challenge",
                "what_it_tests": "what this reveals",
                "good_answer_looks_like": "what a working prompt looks like",
                "follow_up": "follow up",
                "probe_if_weak": "probe"
            }}
        ]
    }},
    "reverse_interview": {{
        "title": "Your Turn",
        "intro": "Now it is your turn. Ask me anything.",
        "score_criteria": {{
            "high_value_questions": ["growth", "team", "challenges", "impact"],
            "red_flag_questions": ["only salary", "only benefits", "how soon promoted"]
        }}
    }}
}}
"""

    response = ask_gpt4o(prompt)
    result = parse_json(response)
    print("[QUESTION GEN] Questions generated for all 4 rounds")
    return result