from azure.cosmos import CosmosClient, exceptions
from shared.config import config
from datetime import datetime
import time

_client = CosmosClient(config.COSMOS_ENDPOINT, config.COSMOS_KEY)
_db     = _client.get_database_client(config.COSMOS_DATABASE)

def col(name):
    return _db.get_container_client(name)

# ── Candidate Operations ─────────────────────────────────────────
def save_candidate(candidate: dict):
    col("candidates").upsert_item(candidate)
    print(f"[DB] Candidate saved: {candidate['id']}")

def get_candidate(cid: str) -> dict:
    return col("candidates").read_item(cid, partition_key=cid)

def update_candidate(cid: str, updates: dict) -> dict:
    c = get_candidate(cid)
    c.update(updates)
    col("candidates").upsert_item(c)
    print(f"[DB] Candidate updated: {cid}")
    return c

def get_all_candidates() -> list:
    return list(col("candidates").read_all_items())

def get_candidates_by_status(status: str) -> list:
    q = f"SELECT * FROM c WHERE c.status = '{status}'"
    return list(col("candidates").query_items(
        query=q, enable_cross_partition_query=True))

def get_candidates_by_job(job_id: str) -> list:
    q = f"SELECT * FROM c WHERE c.job_id = '{job_id}'"
    return list(col("candidates").query_items(
        query=q, enable_cross_partition_query=True))

# ── Job Operations ───────────────────────────────────────────────
def save_job(job: dict):
    col("jobs").upsert_item(job)
    print(f"[DB] Job saved: {job['id']}")

def get_job(job_id: str) -> dict:
    if not job_id:
        return None
    try:
        return col("jobs").read_item(job_id, partition_key=job_id)
    except Exception:
        return None

def update_job(job_id: str, updates: dict) -> dict:
    job = get_job(job_id)
    if not job:
        return None
    job.update(updates)
    col("jobs").upsert_item(job)
    return job

def get_active_jobs() -> list:
    q = "SELECT * FROM c WHERE c.status = 'active'"
    return list(col("jobs").query_items(
        query=q, enable_cross_partition_query=True))

# ── HR User Operations ───────────────────────────────────────────
def save_hr_user(hr: dict):
    col("hr_users").upsert_item(hr)
    print(f"[DB] HR user saved: {hr['id']}")

def get_hr_user(hr_id: str) -> dict:
    if not hr_id:
        return None
    try:
        return col("hr_users").read_item(hr_id, partition_key=hr_id)
    except Exception:
        return None

def get_hr_by_email(email: str) -> dict:
    q = f"SELECT * FROM c WHERE c.email = '{email}'"
    results = list(col("hr_users").query_items(
        query=q, enable_cross_partition_query=True))
    return results[0] if results else None

def get_all_hr_users() -> list:
    return list(col("hr_users").read_all_items())

def update_hr_user(hr_id: str, updates: dict) -> dict:
    hr = get_hr_user(hr_id)
    if not hr:
        return None
    hr.update(updates)
    col("hr_users").upsert_item(hr)
    return hr

# ── Interviewer Operations ───────────────────────────────────────
def save_interviewer(interviewer: dict):
    col("interviewers").upsert_item(interviewer)
    print(f"[DB] Interviewer saved: {interviewer['id']}")

def get_interviewer(iid: str) -> dict:
    try:
        return col("interviewers").read_item(iid, partition_key=iid)
    except exceptions.CosmosResourceNotFoundError:
        return None

def get_interviewer_by_email(email: str) -> dict:
    q = f"SELECT * FROM c WHERE c.email = '{email}'"
    results = list(col("interviewers").query_items(
        query=q, enable_cross_partition_query=True))
    return results[0] if results else None

def get_all_interviewers() -> list:
    return list(col("interviewers").read_all_items())

def get_active_interviewers() -> list:
    q = "SELECT * FROM c WHERE c.status = 'active'"
    return list(col("interviewers").query_items(
        query=q, enable_cross_partition_query=True))

def update_interviewer(iid: str, updates: dict) -> dict:
    i = get_interviewer(iid)
    if not i:
        return None
    i.update(updates)
    col("interviewers").upsert_item(i)
    return i

# ── Interview Assignment Operations ─────────────────────────────
def save_assignment(assignment: dict):
    col("interview_assignments").upsert_item(assignment)
    print(f"[DB] Assignment saved: {assignment['id']}")

def get_assignment(aid: str) -> dict:
    try:
        return col("interview_assignments").read_item(
            aid, partition_key=aid)
    except exceptions.CosmosResourceNotFoundError:
        return None

def get_assignment_by_candidate(candidate_id: str) -> dict:
    q = f"SELECT * FROM c WHERE c.candidate_id = '{candidate_id}' AND c.status != 'completed'"
    results = list(col("interview_assignments").query_items(
        query=q, enable_cross_partition_query=True))
    return results[0] if results else None

def get_all_assignments() -> list:
    return list(col("interview_assignments").read_all_items())

def update_assignment(aid: str, updates: dict) -> dict:
    a = get_assignment(aid)
    if not a:
        return None
    a.update(updates)
    col("interview_assignments").upsert_item(a)
    return a

def add_assignment_timeline(aid: str,
                             event: str,
                             detail: str):
    """Add event to assignment timeline."""
    a = get_assignment(aid)
    if not a:
        return
    timeline = a.get("timeline", [])
    timeline.append({
        "time":   datetime.utcnow().isoformat(),
        "event":  event,
        "detail": detail
    })
    a["timeline"] = timeline
    col("interview_assignments").upsert_item(a)

# ── Audit Operations ─────────────────────────────────────────────
def audit(cid: str, agent: str, action: str, data: dict):
    entry = {
        "id":           f"{cid}-{agent}-{int(time.time())}",
        "candidate_id": cid,
        "agent":        agent,
        "action":       action,
        "data":         data,
        "timestamp":    datetime.utcnow().isoformat()
    }
    col("audit").upsert_item(entry)
    print(f"[AUDIT] {agent} → {action}")

def write_audit(cid: str, agent: str,
                action: str, data: dict):
    audit(cid, agent, action, data)

def get_audit_trail(cid: str) -> list:
    q = f"SELECT * FROM c WHERE c.candidate_id = '{cid}'"
    return list(col("audit").query_items(
        query=q, enable_cross_partition_query=True))

# ── Talent Pool Operations ───────────────────────────────────────
def add_to_talent_pool(candidate: dict):
    entry = {
        "id":           f"pool-{candidate['id']}",
        "candidate_id": candidate["id"],
        "name":         candidate.get("name"),
        "email":        candidate.get("email"),
        "skills":       candidate.get("skills", []),
        "score":        candidate.get("final_score") or
                        candidate.get("resume_score"),
        "role_applied": candidate.get("applied_role"),
        "added_at":     datetime.utcnow().isoformat(),
        "contacted_again": False
    }
    col("talent_pool").upsert_item(entry)
    print(f"[DB] Added to talent pool: {candidate['id']}")

def get_talent_pool() -> list:
    return list(col("talent_pool").read_all_items())

# ── Analytics ────────────────────────────────────────────────────
def get_pipeline_stats() -> dict:
    all_candidates = get_all_candidates()
    total = len(all_candidates)
    stats = {
        "total":           total,
        "applied":         0,
        "screened":        0,
        "ai_interview":    0,
        "human_interview": 0,
        "hired":           0,
        "rejected":        0,
    }
    for c in all_candidates:
        status = c.get("status", "applied")
        if status == "hired":
            stats["hired"] += 1
        elif status == "rejected":
            stats["rejected"] += 1
        elif "waiting" in status or "interview" in status:
            stats["human_interview"] += 1
        elif status == "screened":
            stats["screened"] += 1
        elif status == "ai_interview_complete":
            stats["ai_interview"] += 1
        else:
            stats["applied"] += 1
    return stats

def update_job(job_id: str, updates: dict):
    if not job_id:
        return
    try:
        job = col("jobs").read_item(job_id, partition_key=job_id)
        job.update(updates)
        col("jobs").upsert_item(job)
    except Exception as e:
        print(f"[DB] Job update error: {e}")

def get_bias_report() -> dict:
    all_candidates = get_all_candidates()
    total  = len(all_candidates)
    hired  = [c for c in all_candidates
               if c.get("status") == "hired"]
    avg_score = (
        sum(c.get("resume_score", 0) or 0
            for c in all_candidates) / total
        if total > 0 else 0
    )
    return {
        "total_processed":  total,
        "total_hired":      len(hired),
        "hire_rate":        round(len(hired) / total * 100, 1)
                            if total > 0 else 0,
        "avg_resume_score": round(avg_score, 1),
    }