from azure.cosmos import CosmosClient, exceptions
from shared.config import config
from datetime import datetime
import time

# ── Connection ──────────────────────────────────────────────────
_client = CosmosClient(config.COSMOS_ENDPOINT, config.COSMOS_KEY)
_db     = _client.get_database_client(config.COSMOS_DATABASE)

def col(name):
    return _db.get_container_client(name)

# ── Candidate Operations ────────────────────────────────────────
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
    query = f"SELECT * FROM c WHERE c.status = '{status}'"
    return list(col("candidates").query_items(
        query=query,
        enable_cross_partition_query=True
    ))

def get_candidates_by_job(job_id: str) -> list:
    query = f"SELECT * FROM c WHERE c.job_id = '{job_id}'"
    return list(col("candidates").query_items(
        query=query,
        enable_cross_partition_query=True
    ))

# ── Job Configuration Operations ────────────────────────────────
def save_job(job: dict):
    col("jobs").upsert_item(job)
    print(f"[DB] Job saved: {job['id']}")

def get_job(job_id: str) -> dict:
    try:
        return col("jobs").read_item(job_id, partition_key=job_id)
    except exceptions.CosmosResourceNotFoundError:
        return None

def update_job(job_id: str, updates: dict) -> dict:
    job = get_job(job_id)
    if not job:
        return None
    job.update(updates)
    col("jobs").upsert_item(job)
    return job

def get_active_jobs() -> list:
    query = "SELECT * FROM c WHERE c.status = 'active'"
    return list(col("jobs").query_items(
        query=query,
        enable_cross_partition_query=True
    ))

# ── Audit Operations ────────────────────────────────────────────
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

# Keep old name for compatibility
def write_audit(cid: str, agent: str,
                action: str, data: dict):
    audit(cid, agent, action, data)

def get_audit_trail(cid: str) -> list:
    query = f"SELECT * FROM c WHERE c.candidate_id = '{cid}'"
    return list(col("audit").query_items(
        query=query,
        enable_cross_partition_query=True
    ))

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

def get_talent_pool_by_skills(skills: list) -> list:
    results = []
    all_entries = get_talent_pool()
    for entry in all_entries:
        entry_skills = [s.lower() for s in entry.get("skills", [])]
        for skill in skills:
            if skill.lower() in entry_skills:
                results.append(entry)
                break
    return results

# ── TalentBlitz Operations ───────────────────────────────────────
def save_talentblitz_event(event: dict):
    col("events").upsert_item(event)
    print(f"[DB] TalentBlitz event saved: {event['id']}")

def get_talentblitz_event(event_id: str) -> dict:
    try:
        return col("events").read_item(
            event_id, partition_key=event_id
        )
    except exceptions.CosmosResourceNotFoundError:
        return None

# ── Analytics Queries ────────────────────────────────────────────
def get_pipeline_stats() -> dict:
    all_candidates = get_all_candidates()
    stats = {
        "total":           len(all_candidates),
        "applied":         0,
        "screened":        0,
        "ai_interview":    0,
        "human_interview": 0,
        "hired":           0,
        "rejected":        0,
        "talent_pool":     0
    }
    for c in all_candidates:
        status = c.get("status", "applied")
        if status in stats:
            stats[status] += 1
        elif "interview" in status:
            stats["human_interview"] += 1
        elif "waiting" in status:
            stats["human_interview"] += 1
    return stats

def get_bias_report() -> dict:
    all_candidates  = get_all_candidates()
    total           = len(all_candidates)
    hired           = [c for c in all_candidates
                       if c.get("status") == "hired"]
    rejected        = [c for c in all_candidates
                       if c.get("status") == "rejected"]
    avg_score       = (
        sum(c.get("resume_score", 0) or 0
            for c in all_candidates) / total
        if total > 0 else 0
    )
    return {
        "total_processed":  total,
        "total_hired":      len(hired),
        "total_rejected":   len(rejected),
        "hire_rate":        round(len(hired) / total * 100, 1)
                            if total > 0 else 0,
        "avg_resume_score": round(avg_score, 1),
        "audit_entries":    len(list(
            col("audit").read_all_items()
        ))
    }