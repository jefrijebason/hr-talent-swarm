from shared.openai_client import ask_gpt4o_mini, parse_json

def score_job_description(jd_text: str) -> dict:
    """
    Analyse JD quality before posting.
    Finds issues and suggests improvements.
    """
    print("[JD SCORER] Analysing job description quality...")

    prompt = f"""
You are an expert in inclusive hiring and job description quality.
Analyse this job description and find all issues.

JOB DESCRIPTION:
{jd_text}

Check for:
1. Exclusionary language (rockstar, ninja, guru)
2. Unrealistic experience requirements
3. Too many requirements (more than 8 is too many)
4. Missing salary range
5. Gendered language
6. Age-discriminating language
7. Vague requirements that mean nothing
8. Requirements for tools older than stated experience

Return ONLY valid JSON:
{{
    "overall_quality": 0-10,
    "issues": [
        {{
            "type": "issue type",
            "found": "exact text found",
            "problem": "why this is a problem",
            "fix": "how to fix it",
            "severity": "High/Medium/Low"
        }}
    ],
    "statistics": {{
        "requirements_count": 0,
        "recommended_count": 7,
        "has_salary_range": true/false,
        "exclusionary_words_found": ["word1"],
        "estimated_application_impact": "X% fewer applications due to issues"
    }},
    "improved_jd": "complete rewritten JD with all issues fixed",
    "expected_improvement": {{
        "more_applications": "X%",
        "more_diverse": "X%",
        "better_quality": "description"
    }},
    "summary": "2 sentence honest assessment"
}}
"""

    response = ask_gpt4o_mini(prompt)
    result = parse_json(response)
    quality = result.get('overall_quality', 0)
    issues = len(result.get('issues', []))
    print(f"[JD SCORER] Quality: {quality}/10 | Issues found: {issues}")
    return result