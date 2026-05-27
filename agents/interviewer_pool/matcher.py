from shared.cosmos_client import get_active_interviewers
from shared.openai_client import ask_gpt4o, parse_json
from datetime import datetime

def match_interviewers(candidate_skills: list,
                        role_category: str,
                        seniority: str,
                        job_id: str) -> dict:
    """
    Match top 3 interviewers to candidate.
    Returns primary + 2 backups ranked by match score.
    Solves:
    - Skill matching
    - Availability checking
    - Load balancing
    - Seniority matching
    """
    print(f"[MATCHER] Finding interviewers for: {role_category} | {seniority}")

    interviewers = get_active_interviewers()

    if not interviewers:
        print("[MATCHER] No active interviewers found")
        return {"primary": None, "backup_1": None, "backup_2": None}

    scored = []
    for iv in interviewers:
        score = _score_interviewer(
            iv, candidate_skills, role_category, seniority
        )
        if score > 0:
            scored.append({"interviewer": iv, "score": score})

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    print(f"[MATCHER] Scored {len(scored)} interviewers")

    if scored:
        for s in scored[:3]:
            iv = s["interviewer"]
            print(f"[MATCHER]  {iv['name']}: {s['score']}/100")

    return {
        "primary":  scored[0]["interviewer"] if len(scored) > 0 else None,
        "backup_1": scored[1]["interviewer"] if len(scored) > 1 else None,
        "backup_2": scored[2]["interviewer"] if len(scored) > 2 else None,
        "all_scored": scored
    }

def _score_interviewer(interviewer: dict,
                        candidate_skills: list,
                        role_category: str,
                        seniority: str) -> int:
    """Score one interviewer against candidate requirements."""
    score = 0

    # 1. Skill match (40 points)
    iv_skills = [s.lower() for s in
                 interviewer.get("expertise_skills", [])]
    cand_skills = [s.lower() for s in candidate_skills]

    if cand_skills:
        matched = sum(1 for s in cand_skills if s in iv_skills)
        skill_score = (matched / len(cand_skills)) * 40
        score += skill_score

    # 2. Seniority match (20 points)
    seniority_map = {
        "intern": 1, "junior": 2, "mid": 3,
        "senior": 4, "lead": 5, "manager": 6,
        "director": 7, "vp": 8, "cexec": 9
    }
    cand_level = seniority_map.get(seniority, 3)
    iv_level   = seniority_map.get(
        interviewer.get("seniority", "mid"), 3
    )

    # Interviewer should be same or higher level
    if iv_level >= cand_level:
        score += 20
    elif iv_level == cand_level - 1:
        score += 10

    # 3. Availability (20 points)
    max_week  = interviewer.get("max_per_week", 3)
    curr_book = interviewer.get("current_booked", 0)
    if curr_book < max_week:
        available_ratio = (max_week - curr_book) / max_week
        score += available_ratio * 20

    # 4. Response rate (10 points)
    response_rate = interviewer.get("response_rate", 100)
    score += (response_rate / 100) * 10

    # 5. Load balancing (10 points)
    # Prefer interviewers with fewer recent interviews
    total_done = interviewer.get("total_done", 0)
    if total_done < 10:
        score += 10
    elif total_done < 30:
        score += 7
    elif total_done < 50:
        score += 5
    else:
        score += 3

    return round(score)