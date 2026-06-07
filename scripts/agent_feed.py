from datetime import datetime
from collections import deque
import threading

# Thread-safe in-memory feed (last 200 entries)
_feed_lock = threading.Lock()
_feed = deque(maxlen=200)

def log_agent(agent: str, action: str, detail: str = "", candidate_id: str = ""):
    """Log an agent action to the live feed."""
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "action": action,
        "detail": detail,
        "candidate_id": candidate_id,
    }
    with _feed_lock:
        _feed.append(entry)

def get_feed(limit: int = 50) -> list:
    """Get recent feed entries."""
    with _feed_lock:
        return list(_feed)[-limit:]

def clear_feed():
    with _feed_lock:
        _feed.clear()