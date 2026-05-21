from shared.openai_client import ask_gpt4o_mini, parse_json

def generate_growth_report(candidate: dict,
                            profile: dict,
                            was_hired: bool) -> dict:
    """
    Generate personalized growth report for every candidate.
    Hired or rejected — everyone gets real value.
    """
    print("[GROWTH] Generating candidate growth report...")

    growth_data = profile.get('growth_report_for_candidate', {})
    market = profile.get('market_intelligence', {})

    prompt = f"""
Write a warm, honest, genuinely helpful growth report
for this candidate. They {'got the job' if was_hired else 'were not selected'}.

Either way they deserve real value from this experience.
Never be generic. Always be specific to their profile.

CANDIDATE: {candidate.get('name')}
ROLE APPLIED: {candidate.get('applied_role')}
AI READINESS SCORE: {profile.get('overall_ai_score')}/100
PROFILE TYPE: {profile.get('profile_type')}

STRENGTHS TO HIGHLIGHT:
{growth_data.get('strengths_to_share', [])}

GROWTH AREAS:
{growth_data.get('growth_areas_to_share', [])}

MARKET VALUE:
{growth_data.get('market_value_insight')}

RESOURCES:
{growth_data.get('resources', [])}

Write a complete growth report email. Return ONLY valid JSON:
{{
    "subject": "Your Personal AI Readiness Report — [Role]",
    "body_html": "complete HTML email body",
    "key_insights": ["insight 1", "insight 2", "insight 3"]
}}

The email must include:
1. Warm opening (outcome-appropriate)
2. Their AI Readiness Score with context
3. 3 specific genuine strengths
4. 2 honest growth areas with specific resources
5. Market value insight (honest salary guidance)
6. One actionable thing to do this week
7. Warm closing that makes them feel respected

Make this so valuable they share it with friends.
"""

    response = ask_gpt4o_mini(prompt)
    result = parse_json(response)
    print("[GROWTH] Growth report generated")
    return result