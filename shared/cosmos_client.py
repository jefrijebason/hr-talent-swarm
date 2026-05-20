from azure.cosmos import CosmosClient
from shared.config import config
from datetime import datetime
import time

# Create connection
_client = CosmosClient(config.COSMOS_ENDPOINT, config.COSMOS_KEY)
_db = _client.get_database_client(config.COSMOS_DATABASE)

def get_container(name: str):
    return _db.get_container_client(name)

def save_candidate(candidate: dict):
    get_container("candidates").upsert_item(candidate)
    print(f"[DB] Candidate saved: {candidate['id']}")

def get_candidate(candidate_id: str) -> dict:
    return get_container("candidates").read_item(
        candidate_id,
        partition_key=candidate_id
    )

def update_candidate(candidate_id: str, updates: dict) -> dict:
    candidate = get_candidate(candidate_id)
    candidate.update(updates)
    get_container("candidates").upsert_item(candidate)
    print(f"[DB] Candidate updated: {candidate_id}")
    return candidate

def write_audit(candidate_id: str, agent: str,
                action: str, data: dict):
    audit_entry = {
        "id": f"{candidate_id}-{agent}-{int(time.time())}",
        "candidate_id": candidate_id,
        "agent": agent,
        "action": action,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    get_container("audit").upsert_item(audit_entry)
    print(f"[AUDIT] {agent} → {action}")

def add_to_talent_pool(candidate: dict):
    pool_entry = {
        "id": f"pool-{candidate['id']}",
        "candidate_id": candidate["id"],
        "name": candidate.get("name"),
        "email": candidate.get("email"),
        "skills": candidate.get("skills", []),
        "score": candidate.get("final_score"),
        "added_at": datetime.utcnow().isoformat()
    }
    get_container("talent_pool").upsert_item(pool_entry)
    print(f"[DB] Added to talent pool: {candidate['id']}")

def get_all_candidates() -> list:
    container = get_container("candidates")
    return list(container.read_all_items())