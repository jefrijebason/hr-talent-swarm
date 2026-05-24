from shared.openai_client import ask_gpt4o, ask_gpt4o_mini, parse_json
from datetime import datetime

def get_latest_awareness(tech_stack: list,
                          role_category: str,
                          jd_text: str) -> dict:
    """
    Find what changed recently in the candidate's
    technology stack and role domain.
    Feeds into question generation to ensure
    questions cannot be answered from old textbooks.
    """
    print("[AWARENESS] Checking latest developments...")

    current_month = datetime.utcnow().strftime("%B %Y")
    awareness     = {}

    # Get awareness for each technology
    for tech in tech_stack[:5]:  # Top 5 technologies
        awareness[tech] = _get_tech_awareness(
            tech, current_month
        )

    # Get domain-level awareness
    awareness["domain"] = _get_domain_awareness(
        role_category, current_month, jd_text
    )

    # Generate interview questions from awareness
    awareness["interview_questions"] = _generate_awareness_questions(
        awareness, tech_stack, role_category
    )

    print(f"[AWARENESS] Covered {len(tech_stack[:5])} technologies")
    print(f"[AWARENESS] Generated {len(awareness['interview_questions'])} awareness questions")
    return awareness

def _get_tech_awareness(technology: str,
                         current_month: str) -> dict:
    """Get latest developments for one technology."""

    prompt = f"""
You are a senior engineer keeping up with {technology}.
It is {current_month}.

What has genuinely changed or emerged in {technology}
in the last 6 months that a working professional
should know about?

Focus on:
1. New versions and what changed
2. Best practices that evolved or changed
3. Tools that emerged or became standard
4. Community debates happening right now
5. Things that became deprecated or discouraged
6. Performance improvements or breaking changes

Be specific and factual. Do not make things up.
If you are not sure of exact recent changes,
focus on fundamental shifts in thinking.

Return ONLY valid JSON:
{{
    "technology": "{technology}",
    "key_changes": [
        {{
            "change": "what changed",
            "impact": "why it matters",
            "interview_angle": "how to test awareness of this"
        }}
    ],
    "deprecated_practices": ["practice1", "practice2"],
    "emerging_tools": ["tool1", "tool2"],
    "community_debates": ["debate1"],
    "one_question_to_test_currency": "a specific question that cannot be answered from a 2022 textbook"
}}
"""

    try:
        response = ask_gpt4o_mini(prompt)
        return parse_json(response)
    except Exception as e:
        print(f"[AWARENESS] Error for {technology}: {e}")
        return {
            "technology":    technology,
            "key_changes":   [],
            "one_question_to_test_currency":
                f"What recent changes in {technology} have affected your work?"
        }

def _get_domain_awareness(role_category: str,
                           current_month: str,
                           jd_text: str) -> dict:
    """Get latest developments for the entire domain."""

    domain_map = {
        "software_development": "software engineering practices",
        "data_analytics":        "data analytics and BI",
        "ai_ml":                 "AI and machine learning",
        "infrastructure":        "cloud infrastructure and DevOps",
        "product_design":        "UX and product design",
        "security":              "cybersecurity",
        "sales":                 "B2B sales and business development",
        "marketing":             "digital marketing and growth",
        "operations":            "business operations and management",
        "finance_legal":         "finance, accounting, and legal",
        "people_hr":             "HR and people management",
        "specialized_domain":    "specialized technical domain"
    }

    domain = domain_map.get(role_category, role_category)

    prompt = f"""
You are an expert in {domain}.
It is {current_month}.

What are the most significant shifts happening
in {domain} right now that professionals in
this field must be aware of?

Consider this job context:
{jd_text[:500]}

Return ONLY valid JSON:
{{
    "domain": "{domain}",
    "major_shifts": [
        {{
            "shift": "what is changing",
            "why_it_matters": "business impact",
            "what_good_looks_like": "how leaders in field respond"
        }}
    ],
    "hot_topics": ["topic1", "topic2", "topic3"],
    "skills_becoming_critical": ["skill1", "skill2"],
    "skills_becoming_obsolete": ["skill1"],
    "live_task_idea": "a realistic task that tests current awareness"
}}
"""

    try:
        response = ask_gpt4o_mini(prompt)
        return parse_json(response)
    except Exception as e:
        print(f"[AWARENESS] Domain error: {e}")
        return {
            "domain":       domain,
            "major_shifts": [],
            "hot_topics":   [],
            "live_task_idea": f"Describe how recent changes in {domain} affect your work"
        }

def _generate_awareness_questions(awareness: dict,
                                   tech_stack: list,
                                   role_category: str) -> list:
    """
    Generate specific questions that test genuine
    current awareness. Cannot be answered from
    old textbooks or copied answers.
    """
    questions = []

    # One question per technology
    for tech in tech_stack[:3]:
        tech_data = awareness.get(tech, {})
        base_q    = tech_data.get(
            "one_question_to_test_currency",
            f"What recent changes in {tech} have you noticed?"
        )
        questions.append({
            "technology":    tech,
            "question":      base_q,
            "type":          "latest_awareness",
            "cannot_google": True
        })

    # Domain-level question
    domain_data = awareness.get("domain", {})
    hot_topics  = domain_data.get("hot_topics", [])
    if hot_topics:
        questions.append({
            "technology": "domain",
            "question": (
                f"The field is currently debating "
                f"{hot_topics[0]}. "
                f"Where do you stand and why?"
            ),
            "type":          "domain_awareness",
            "cannot_google": True
        })

    # Live task from domain
    live_task = domain_data.get("live_task_idea")
    if live_task:
        questions.append({
            "technology": "domain",
            "question":   live_task,
            "type":       "live_task",
            "cannot_google": True
        })

    return questions

def generate_live_task(role_category: str,
                        tech_stack: list,
                        jd_text: str,
                        awareness: dict) -> dict:
    """
    Generate the Round 5 live task based on
    latest awareness and JD requirements.
    This is a real task — not a textbook question.
    """
    print("[AWARENESS] Generating live task...")

    domain_data = awareness.get("domain", {})
    hot_topics  = domain_data.get("hot_topics", [])
    shifts      = domain_data.get("major_shifts", [])

    context = ""
    if hot_topics:
        context += f"Hot topics right now: {', '.join(hot_topics[:3])}. "
    if shifts:
        context += f"Major shift: {shifts[0].get('shift', '')}. "

    prompt = f"""
Create a challenging live task for a job interview.

Role category: {role_category}
Technologies:  {', '.join(tech_stack[:4])}
Current context: {context}
JD requirement snippet: {jd_text[:400]}

The task must:
1. Be based on something REAL happening in the field now
2. Take 10-15 minutes to complete
3. Have a clear deliverable
4. Test practical judgment not memorized knowledge
5. Be impossible to complete well with a 2022 textbook
6. Require the candidate to take a position and defend it

Return ONLY valid JSON:
{{
    "task_title":    "short compelling title",
    "task_prompt":   "complete task description (3-4 sentences)",
    "deliverable":   "exactly what candidate must produce",
    "time_minutes":  15,
    "success_looks_like": ["criterion1", "criterion2", "criterion3"],
    "weak_answer_looks_like": "what a poor answer looks like",
    "what_it_tests": "what this reveals about the candidate"
}}
"""

    try:
        response = ask_gpt4o(prompt)
        result   = parse_json(response)
        print(f"[AWARENESS] Live task: {result.get('task_title')}")
        return result
    except Exception as e:
        print(f"[AWARENESS] Live task error: {e}")
        return {
            "task_title":   "Domain Evaluation Task",
            "task_prompt":  f"Evaluate current best practices in {role_category} and propose improvements.",
            "deliverable":  "Written analysis with recommendations",
            "time_minutes": 15,
            "success_looks_like": ["Current awareness", "Clear reasoning", "Practical recommendations"]
        }