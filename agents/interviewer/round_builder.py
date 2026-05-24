from shared.openai_client import ask_gpt4o, parse_json
from agents.interviewer.jd_intelligence import (
    analyse_jd, get_default_human_rounds, ROLE_CONFIGS
)

def build_interview_rounds(jd_text: str,
                            resume_text: str,
                            interview_mode: str = "standard",
                            custom_human_rounds: list = None) -> dict:
    """
    Build complete interview round configuration
    for any JD and any role type.

    Returns exactly what rounds to run,
    in what order, with what focus.
    """
    print("[ROUND BUILDER] Building interview rounds...")

    # Step 1 — Analyse the JD
    jd_intel = analyse_jd(jd_text)
    category  = jd_intel.get("role_category", "software_development")
    seniority = jd_intel.get("seniority_level", "mid")
    config    = ROLE_CONFIGS.get(category, ROLE_CONFIGS["software_development"])

    # Step 2 — Determine which AI rounds to include
    ai_rounds = _build_ai_rounds(
        jd_intel, resume_text, interview_mode
    )

    # Step 3 — Determine coding round
    coding_config = _build_coding_config(
        jd_intel, interview_mode
    )

    # Step 4 — Get human rounds
    if custom_human_rounds:
        # Recruiter configured custom rounds
        human_rounds = _sort_rounds(custom_human_rounds)
    else:
        # Use defaults based on role + seniority
        human_rounds = get_default_human_rounds(
            category, seniority
        )

    # Step 5 — Apply mode overrides
    if interview_mode == "executive":
        ai_rounds["enabled"]    = False
        coding_config["enabled"] = False
        print("[ROUND BUILDER] Executive mode: AI rounds disabled")

    elif interview_mode == "express":
        ai_rounds["rounds"] = ai_rounds["rounds"][:2]
        coding_config["duration_minutes"] = 20
        human_rounds = human_rounds[:1]
        print("[ROUND BUILDER] Express mode: compressed rounds")

    # Step 6 — Build final pipeline order
    pipeline = _build_pipeline_order(
        coding_config, ai_rounds, human_rounds, interview_mode
    )

    result = {
        "jd_intelligence":  jd_intel,
        "role_category":    category,
        "seniority":        seniority,
        "interview_mode":   interview_mode,
        "coding_config":    coding_config,
        "ai_rounds":        ai_rounds,
        "human_rounds":     human_rounds,
        "pipeline_order":   pipeline,
        "total_rounds":     len(pipeline),
        "estimated_time":   _estimate_time(pipeline)
    }

    print(f"[ROUND BUILDER] Pipeline: {[p['name'] for p in pipeline]}")
    print(f"[ROUND BUILDER] Est. time: {result['estimated_time']}")
    return result

def _build_ai_rounds(jd_intel: dict,
                      resume_text: str,
                      mode: str) -> dict:
    """Build AI interview rounds based on role."""
    category  = jd_intel.get("role_category")
    seniority = jd_intel.get("seniority_level")
    stack     = jd_intel.get("tech_stack", [])

    rounds = [
        {
            "round_number": 1,
            "name":         "Resume Truth Test",
            "duration":     15,
            "objective":    "Verify resume claims with depth",
            "focus":        "specific claims from their resume"
        },
        {
            "round_number": 2,
            "name":         "Latest Technology Awareness",
            "duration":     15,
            "objective":    "Test currency with recent changes",
            "focus":        f"recent changes in {', '.join(stack[:3])}"
        },
        {
            "round_number": 3,
            "name":         "Problem Solving With AI",
            "duration":     15,
            "objective":    "Test AI-augmented problem solving",
            "focus":        "real problem from JD requirements"
        },
        {
            "round_number": 4,
            "name":         "JD Gap Challenge",
            "duration":     15,
            "objective":    "Test learning agility on gaps",
            "focus":        "their specific resume vs JD gaps"
        },
        {
            "round_number": 5,
            "name":         "Live Domain Task",
            "duration":     15,
            "objective":    "Real task based on latest evaluation",
            "focus":        f"current landscape in {category}"
        },
        {
            "round_number": 6,
            "name":         "Reverse Interview",
            "duration":     10,
            "objective":    "Candidate interviews the AI",
            "focus":        "quality of questions asked"
        }
    ]

    # Adjust for seniority
    if seniority in ["intern", "junior"]:
        # Remove hardest rounds for juniors
        rounds = [r for r in rounds
                  if r["round_number"] not in [4, 5]]

    return {
        "enabled": True,
        "rounds":  rounds,
        "total_duration": sum(r["duration"] for r in rounds)
    }

def _build_coding_config(jd_intel: dict,
                          mode: str) -> dict:
    """Build coding round configuration."""
    category     = jd_intel.get("role_category")
    coding_type  = jd_intel.get("coding_type", "none")
    stack        = jd_intel.get("tech_stack", [])
    config       = ROLE_CONFIGS.get(category, {})
    coding_needed = config.get("coding_round", False)

    if not coding_needed or coding_type == "none":
        return {
            "enabled":        False,
            "reason":         f"Not required for {category} roles"
        }

    # Configure based on coding type
    if coding_type == "algorithms_and_design":
        return {
            "enabled":          True,
            "type":             "algorithms_and_design",
            "duration_minutes": 45,
            "problems":         2,
            "languages":        stack if stack else ["Python"],
            "anti_malpractice": True,
            "test_cases":       3,
            "description":      "Algorithm + system design problems"
        }

    elif coding_type == "sql_and_data":
        return {
            "enabled":          True,
            "type":             "sql_and_data",
            "duration_minutes": 30,
            "problems":         2,
            "languages":        ["SQL", "Python"],
            "anti_malpractice": True,
            "test_cases":       2,
            "description":      "SQL queries + data modeling"
        }

    elif coding_type == "ml_implementation":
        return {
            "enabled":          True,
            "type":             "ml_implementation",
            "duration_minutes": 45,
            "problems":         1,
            "languages":        ["Python"],
            "anti_malpractice": True,
            "test_cases":       2,
            "description":      "ML model implementation + evaluation"
        }

    elif coding_type == "domain_specific":
        return {
            "enabled":          True,
            "type":             "domain_specific",
            "duration_minutes": 30,
            "problems":         1,
            "languages":        stack if stack else ["Python"],
            "anti_malpractice": True,
            "test_cases":       2,
            "description":      f"Domain-specific task for {category}"
        }

    return {"enabled": False, "reason": "Type not recognized"}

def _sort_rounds(human_rounds: list) -> list:
    """Sort human rounds by position field."""
    return sorted(human_rounds,
                  key=lambda r: r.get("position", 99))

def _build_pipeline_order(coding: dict,
                           ai: dict,
                           human: list,
                           mode: str) -> list:
    """Build the complete ordered pipeline."""
    pipeline = []
    step     = 1

    # Always first: Resume screening
    pipeline.append({
        "step":     step,
        "name":     "Resume Screening",
        "type":     "ai_screening",
        "duration": 5,
        "agent":    "SCREENER"
    })
    step += 1

    # Coding round (if enabled) — before AI interview
    if coding.get("enabled"):
        pipeline.append({
            "step":     step,
            "name":     "Coding Round",
            "type":     "coding",
            "duration": coding.get("duration_minutes", 45),
            "agent":    "CODING_ROUND",
            "config":   coding
        })
        step += 1

    # AI Interview rounds
    if ai.get("enabled"):
        for r in ai.get("rounds", []):
            pipeline.append({
                "step":     step,
                "name":     f"AI Round {r['round_number']}: {r['name']}",
                "type":     "ai_interview",
                "duration": r["duration"],
                "agent":    "INTERVIEWER",
                "config":   r
            })
            step += 1

    # Human rounds in configured order
    for hr in human:
        pipeline.append({
            "step":      step,
            "name":      hr.get("round_name", f"Human Round {step}"),
            "type":      "human",
            "duration":  hr.get("duration_minutes", 60),
            "agent":     "HUMAN",
            "config":    hr
        })
        step += 1

    return pipeline

def _estimate_time(pipeline: list) -> str:
    """Estimate total candidate time."""
    total_minutes = sum(p.get("duration", 0) for p in pipeline)
    ai_minutes    = sum(
        p.get("duration", 0) for p in pipeline
        if p.get("type") in ["ai_screening", "ai_interview", "coding"]
    )
    human_days    = sum(
        1 for p in pipeline if p.get("type") == "human"
    )

    return (
        f"{ai_minutes} min AI assessment + "
        f"{human_days} human interview day(s)"
    )