from shared.openai_client import ask_gpt4o, parse_json

def build_ai_readiness_profile(candidate: dict,
                                analysis: dict,
                                round_scores: dict,
                                jd_text: str) -> dict:
    """
    Build the complete AI Readiness Profile.
    This goes to the human interviewer as a briefing.
    """
    print("[PROFILE] Building AI Readiness Profile...")

    prompt = f"""
You are building a comprehensive AI Readiness Profile
for a hiring manager. Be honest, specific, and actionable.

CANDIDATE INFO:
Name: {candidate.get('name')}
Role: {candidate.get('applied_role')}
Expected CTC: {candidate.get('expected_ctc')}

RESUME VS JD ANALYSIS:
{analysis}

INTERVIEW ROUND SCORES:
Round 1 - Resume Truth:      {round_scores.get('round_1', 0)}/100
Round 2 - Problem Solving:   {round_scores.get('round_2', 0)}/100
Round 3 - Gap Challenge:     {round_scores.get('round_3', 0)}/100
Round 4 - Prompt Engineering:{round_scores.get('round_4', 0)}/100
Reverse Interview:           {round_scores.get('reverse', 0)}/100

JOB DESCRIPTION:
{jd_text}

Build a complete profile. Return ONLY valid JSON:
{{
    "overall_ai_score": 0-100,
    "profile_type": "AI-Native/AI-Assisted/AI-Aware/AI-Resistant",
    "profile_description": "2 sentence description of this type",
    "percentile": "top X% of candidates",

    "dimension_scores": {{
        "resume_verification": 0-100,
        "technical_depth": 0-100,
        "ai_productivity": 0-100,
        "learning_agility": 0-100,
        "prompt_engineering": 0-100,
        "communication": 0-100
    }},

    "jd_alignment": {{
        "perfect_matches_verified": ["skill1", "skill2"],
        "partial_matches_status": ["skill: status"],
        "gaps_handled": ["gap: how they handled it"],
        "bonus_skills": ["skill1"]
    }},

    "strengths": ["specific strength 1", "specific strength 2"],
    "growth_areas": ["specific area 1", "specific area 2"],

    "resume_verification_notes": [
        {{"claim": "what they claimed", "verdict": "Verified/Partial/Unverified", "note": "detail"}}
    ],

    "human_interview_briefing": {{
        "do_not_test_again": ["already verified topics"],
        "focus_on": ["what to probe"],
        "suggested_questions": ["question 1", "question 2", "question 3"],
        "watch_out_for": ["potential concern 1"]
    }},

    "market_intelligence": {{
        "candidate_expected": "their CTC expectation",
        "market_rate": "market range for this profile",
        "assessment": "above/at/below market",
        "recommendation": "specific salary recommendation",
        "retention_risk": "Low/Medium/High",
        "retention_note": "why"
    }},

    "hiring_recommendation": "Strong Hire/Hire/Maybe/No Hire",
    "recommendation_reasoning": "2 sentence honest reasoning",

    "growth_report_for_candidate": {{
        "strengths_to_share": ["strength 1", "strength 2"],
        "growth_areas_to_share": ["area 1", "area 2"],
        "resources": ["resource 1", "resource 2"],
        "market_value_insight": "what to tell them about their market value"
    }}
}}
"""

    response = ask_gpt4o(prompt)
    result = parse_json(response)
    print(f"[PROFILE] AI Readiness Score: {result.get('overall_ai_score')}/100")
    print(f"[PROFILE] Profile Type: {result.get('profile_type')}")
    print(f"[PROFILE] Recommendation: {result.get('hiring_recommendation')}")
    return result