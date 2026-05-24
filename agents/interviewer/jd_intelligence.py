from shared.openai_client import ask_gpt4o, parse_json

# ── Role Category Configs ────────────────────────────────────────
ROLE_CONFIGS = {
    "software_development": {
        "coding_round":       True,
        "coding_type":        "algorithms_and_design",
        "anti_malpractice":   True,
        "portfolio_required": False,
        "assessment_modules": [
            "coding", "system_design",
            "latest_awareness", "gap_challenge", "live_task"
        ],
        "evaluation_dimensions": [
            "code_quality", "system_thinking",
            "ai_productivity", "latest_awareness"
        ],
        "interview_focus": "Technical depth, system design, code quality"
    },

    "data_analytics": {
        "coding_round":       True,
        "coding_type":        "sql_and_data",
        "anti_malpractice":   True,
        "portfolio_required": False,
        "assessment_modules": [
            "sql_task", "data_modeling",
            "latest_awareness", "business_translation"
        ],
        "evaluation_dimensions": [
            "sql_depth", "business_thinking",
            "visualization", "latest_awareness"
        ],
        "interview_focus": "SQL mastery, data modeling, business translation"
    },

    "ai_ml": {
        "coding_round":       True,
        "coding_type":        "ml_implementation",
        "anti_malpractice":   True,
        "portfolio_required": False,
        "assessment_modules": [
            "ml_task", "latest_model_awareness",
            "experimentation_design", "live_task"
        ],
        "evaluation_dimensions": [
            "ml_depth", "research_awareness",
            "experimentation", "latest_awareness"
        ],
        "interview_focus": "ML fundamentals, latest models, experimentation"
    },

    "infrastructure": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "architecture_design", "troubleshooting",
            "latest_awareness", "reliability_thinking"
        ],
        "evaluation_dimensions": [
            "systems_knowledge", "reliability_thinking",
            "troubleshooting", "latest_awareness"
        ],
        "interview_focus": "Architecture, reliability, troubleshooting"
    },

    "product_design": {
        "coding_round":             False,
        "coding_type":              None,
        "anti_malpractice":         True,
        "anti_malpractice_type":    "portfolio_interrogation",
        "portfolio_required":       True,
        "assessment_modules": [
            "portfolio_review", "design_critique",
            "user_research", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "design_thinking", "user_empathy",
            "visual_quality", "latest_awareness"
        ],
        "interview_focus": "Design thinking, user empathy, portfolio depth"
    },

    "security": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "threat_modeling", "incident_scenario",
            "regulatory_knowledge", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "threat_awareness", "regulatory_knowledge",
            "incident_response", "latest_awareness"
        ],
        "interview_focus": "Threat modeling, compliance, incident response"
    },

    "sales": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "role_play", "objection_handling",
            "pipeline_thinking", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "communication", "persuasion",
            "product_knowledge", "latest_awareness"
        ],
        "interview_focus": "Communication, objection handling, pipeline"
    },

    "marketing": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   True,
        "anti_malpractice_type": "portfolio_interrogation",
        "portfolio_required": True,
        "assessment_modules": [
            "portfolio_review", "campaign_analysis",
            "growth_thinking", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "creative_thinking", "data_interpretation",
            "platform_knowledge", "latest_awareness"
        ],
        "interview_focus": "Creative thinking, data analysis, platform depth"
    },

    "operations": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "process_design", "stakeholder_scenario",
            "latest_awareness", "efficiency_thinking"
        ],
        "evaluation_dimensions": [
            "process_thinking", "stakeholder_management",
            "efficiency", "latest_awareness"
        ],
        "interview_focus": "Process design, stakeholder management"
    },

    "finance_legal": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "case_study", "regulatory_knowledge",
            "risk_thinking", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "domain_accuracy", "regulatory_knowledge",
            "risk_thinking", "latest_awareness"
        ],
        "interview_focus": "Domain accuracy, regulatory knowledge, risk"
    },

    "people_hr": {
        "coding_round":       False,
        "coding_type":        None,
        "anti_malpractice":   False,
        "portfolio_required": False,
        "assessment_modules": [
            "people_scenario", "policy_knowledge",
            "conflict_resolution", "latest_awareness"
        ],
        "evaluation_dimensions": [
            "people_judgment", "policy_knowledge",
            "empathy", "latest_awareness"
        ],
        "interview_focus": "People judgment, policy, conflict resolution"
    },

    "specialized_domain": {
        "coding_round":       "auto_detect",
        "coding_type":        "domain_specific",
        "anti_malpractice":   True,
        "portfolio_required": False,
        "assessment_modules": [
            "domain_task", "domain_knowledge",
            "latest_awareness", "scenario"
        ],
        "evaluation_dimensions": [
            "domain_depth", "practical_knowledge",
            "latest_awareness", "problem_solving"
        ],
        "interview_focus": "Deep domain knowledge and practical application"
    }
}

def analyse_jd(jd_text: str) -> dict:
    """
    Analyse any JD and return complete intelligence.
    """
    print("[JD INTEL] Analysing job description...")

    # Truncate JD to avoid filter issues
    safe_jd = jd_text[:1000]

    prompt = f"""
Analyse this job description for HR purposes.

JD:
{safe_jd}

Return ONLY valid JSON with these fields:
{{
    "role_category": "one of: software_development, data_analytics, ai_ml, infrastructure, product_design, security, sales, marketing, operations, finance_legal, people_hr, specialized_domain",
    "role_title": "job title from JD",
    "seniority_level": "one of: intern, junior, mid, senior, lead, manager, director, vp, cexec",
    "tech_stack": ["technology1", "technology2"],
    "domain_keywords": ["keyword1", "keyword2"],
    "coding_needed": true,
    "coding_type": "one of: algorithms_and_design, sql_and_data, ml_implementation, domain_specific, none",
    "primary_skill": "most important skill",
    "key_responsibilities": ["resp1", "resp2"],
    "must_have": ["req1", "req2"],
    "nice_to_have": ["req1"],
    "assessment_approach": "how to assess this role",
    "interview_focus": "what to focus on",
    "estimated_market_rate": "salary range in India",
    "reasoning": "why you categorised this way"
}}
"""

    response = ask_gpt4o(prompt)
    result   = parse_json(response)

    if not result:
        result = _fallback_analysis(jd_text)

    category = result.get("role_category", "software_development")
    config_data = ROLE_CONFIGS.get(
        category, ROLE_CONFIGS["software_development"]
    )

    result["role_config"]          = config_data
    result["coding_round_enabled"] = config_data.get("coding_round", False)
    result["assessment_modules"]   = config_data.get("assessment_modules", [])
    result["portfolio_required"]   = config_data.get("portfolio_required", False)

    print(f"[JD INTEL] Category:  {result.get('role_category')}")
    print(f"[JD INTEL] Seniority: {result.get('seniority_level')}")
    print(f"[JD INTEL] Coding:    {result.get('coding_round_enabled')}")
    print(f"[JD INTEL] Stack:     {result.get('tech_stack')}")

    return result

def _fallback_analysis(jd_text: str) -> dict:
    """Fallback if analysis fails."""
    return {
        "role_category":    "software_development",
        "role_title":       "Software Engineer",
        "seniority_level":  "mid",
        "tech_stack":       ["Python"],
        "domain_keywords":  ["software", "engineering"],
        "coding_needed":    True,
        "coding_type":      "algorithms_and_design",
        "primary_skill":    "Python",
        "key_responsibilities": ["Build software"],
        "must_have":        ["Python experience"],
        "nice_to_have":     [],
        "assessment_approach": "Technical coding assessment",
        "interview_focus":  "Technical depth",
        "estimated_market_rate": "10-20 LPA",
        "reasoning":        "Defaulted to software development"
    }

def get_default_human_rounds(role_category: str,
                              seniority: str) -> list:
    """
    Return default human round configuration
    based on role and seniority.
    Recruiter can modify these on the dashboard.
    """
    base_rounds = []

    # Round 1 — Technical (most roles)
    if role_category not in ["sales", "marketing", "people_hr"]:
        base_rounds.append({
            "round_number":     1,
            "round_name":       "Technical Interview",
            "interviewer_name": "Technical Lead",
            "interviewer_email": "",
            "duration_minutes": 60,
            "focus":            "Technical depth and domain expertise",
            "position":         1,
            "is_required":      True
        })
    else:
        base_rounds.append({
            "round_number":     1,
            "round_name":       "Domain Interview",
            "interviewer_name": "Domain Manager",
            "interviewer_email": "",
            "duration_minutes": 45,
            "focus":            "Domain expertise and experience",
            "position":         1,
            "is_required":      True
        })

    # Round 2 — HR (all roles)
    base_rounds.append({
        "round_number":     2,
        "round_name":       "HR Discussion",
        "interviewer_name": "HR Manager",
        "interviewer_email": "",
        "duration_minutes": 45,
        "focus":            "Culture fit, motivation, salary",
        "position":         2,
        "is_required":      True
    })

    # Add CTO/Leadership round for senior roles
    if seniority in ["lead", "manager", "director", "vp", "cexec"]:
        base_rounds.append({
            "round_number":     3,
            "round_name":       "Leadership Interview",
            "interviewer_name": "CTO / VP Engineering",
            "interviewer_email": "",
            "duration_minutes": 30,
            "focus":            "Vision, leadership, strategic thinking",
            "position":         3,
            "is_required":      True
        })

    return base_rounds