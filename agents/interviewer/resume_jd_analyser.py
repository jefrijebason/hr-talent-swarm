from shared.openai_client import ask_gpt4o, parse_json

def analyse_resume_and_jd(resume_text: str, jd_text: str) -> dict:
    """
    Deep analysis of resume against job description.
    Finds perfect matches, partial matches, gaps, and bonuses.
    This drives all question generation.
    """
    print("[ANALYSER] Analysing resume against JD...")

    prompt = f"""
You are an expert technical recruiter with 15 years experience.
Deeply analyse this candidate's resume against the job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Provide a detailed analysis. Return ONLY valid JSON:
{{
    "candidate_summary": "2 sentence summary of candidate",
    "seniority_level": "Junior/Mid/Senior/Lead",
    "strongest_claim": "their most impressive achievement",
    "most_interesting_claim": "most unique thing about them",
    "perfect_matches": [
        {{
            "skill": "skill name",
            "resume_evidence": "what resume says",
            "jd_requirement": "what JD needs",
            "depth_question": "specific question to verify depth"
        }}
    ],
    "partial_matches": [
        {{
            "skill": "skill name",
            "resume_has": "what they have",
            "jd_needs": "what JD needs",
            "gap": "specific gap",
            "bridge_question": "question to test bridging ability"
        }}
    ],
    "gaps": [
        {{
            "skill": "missing skill",
            "importance": "Critical/Important/Nice to have",
            "learning_question": "question to test learning ability"
        }}
    ],
    "bonus_skills": ["skill1", "skill2"],
    "red_flags": ["any concerns from resume"],
    "jd_key_requirements": ["top 5 requirements from JD"],
    "recommended_focus": "what to focus on in interview",
    "overall_fit_score": 0-100,
    "market_rate": "estimated salary range based on profile"
}}
"""

    response = ask_gpt4o(prompt)
    result = parse_json(response)
    print(f"[ANALYSER] Fit score: {result.get('overall_fit_score')}/100")
    print(f"[ANALYSER] Perfect matches: {len(result.get('perfect_matches', []))}")
    print(f"[ANALYSER] Gaps: {len(result.get('gaps', []))}")
    return result