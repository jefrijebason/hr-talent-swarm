"""
agents/vibe_engineering/problems.py

Pre-baked coding challenges for the Vibe Engineering Challenge.

Each problem has:
  - id, title, description
  - starter_code (Python, runs in Pyodide)
  - test_cases (visible AND hidden — hidden run on submit)
  - bug_description (what's wrong with the code)
  - feature_spec (what the candidate must ADD)
  - reference_solution (used by evaluator for comparison)
  - difficulty + time_limit_minutes
"""

PROBLEMS = {
    # ─────────────────────────────────────────────────────────────
    # Problem 1: Rate Limiter (most common — pick this for demos)
    # ─────────────────────────────────────────────────────────────
    "rate_limiter": {
        "id": "rate_limiter",
        "title": "Fix the Rate Limiter, then Extend It",
        "difficulty": "medium",
        "time_limit_minutes": 30,
        "role_match": ["engineer", "backend", "ml", "data"],

        "description": """
You inherit this rate-limiter from a colleague. It has a subtle bug, and you need
to extend it with a new feature.

## Part 1 — Fix the bug
The `allow_request()` method should let through at most `max_requests` per `window_seconds`
per user. But there's a bug that makes it occasionally allow too many requests through.

## Part 2 — Add the feature
Add a new method `allow_request_sliding(user_id)` that implements a TRUE sliding
window (not fixed buckets). It should be more accurate than the fixed-window version.

## Constraints
- Python only (Pyodide). No external libraries.
- Both `allow_request()` and `allow_request_sliding()` must work on the same instance.
- You're free to use the AI assistant — your interactions are part of the evaluation.
""",

        "starter_code": '''import time
from collections import defaultdict

class RateLimiter:
    """Fixed-window rate limiter. Has a bug somewhere."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 10):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Tracks: user_id -> (window_start_time, request_count)
        self.windows = defaultdict(lambda: (0, 0))

    def allow_request(self, user_id: str) -> bool:
        """
        Returns True if the request is allowed, False if rate-limited.
        Bug: occasionally lets through more than max_requests.
        """
        now = time.time()
        window_start, count = self.windows[user_id]

        # If we're past the window, reset
        if now - window_start > self.window_seconds:
            self.windows[user_id] = (now, 1)
            return True

        # Otherwise check count
        if count < self.max_requests:
            self.windows[user_id] = (window_start, count + 1)
            return True

        return False

    # TODO: Add allow_request_sliding(user_id) here.
    # It should use a true sliding window (not fixed buckets).
''',

        "test_cases_visible": [
            {
                "name": "Basic: 5 requests should all pass",
                "code": '''rl = RateLimiter(max_requests=5, window_seconds=10)
results = [rl.allow_request("alice") for _ in range(5)]
assert results == [True, True, True, True, True], f"Got {results}"
print("PASS: 5 requests all allowed")''',
            },
            {
                "name": "Basic: 6th request should be blocked",
                "code": '''rl = RateLimiter(max_requests=5, window_seconds=10)
for _ in range(5):
    rl.allow_request("bob")
assert rl.allow_request("bob") == False, "6th should be blocked"
print("PASS: 6th request blocked")''',
            },
            {
                "name": "Sliding window method exists",
                "code": '''rl = RateLimiter(max_requests=5, window_seconds=10)
assert hasattr(rl, "allow_request_sliding"), "Missing allow_request_sliding"
result = rl.allow_request_sliding("test")
assert isinstance(result, bool), "Should return bool"
print("PASS: sliding method exists")''',
            },
        ],

        "test_cases_hidden": [
            {
                "name": "Bug check: window boundary",
                "code": '''import time
rl = RateLimiter(max_requests=3, window_seconds=1)
# Fill up
for _ in range(3):
    rl.allow_request("eve")
# Should be blocked
assert rl.allow_request("eve") == False
# Wait past window
time.sleep(1.1)
# Should be allowed again
assert rl.allow_request("eve") == True
print("PASS: window resets correctly")''',
            },
            {
                "name": "Sliding more accurate than fixed",
                "code": '''import time
rl = RateLimiter(max_requests=3, window_seconds=1)
# 3 requests in first half-second
for _ in range(3):
    rl.allow_request_sliding("dan")
time.sleep(0.6)
# Should still be blocked under sliding (3 in last 1s)
blocked = rl.allow_request_sliding("dan") == False
assert blocked, "Sliding should still block — 3 requests in last 1s"
print("PASS: sliding window accurate")''',
            },
        ],

        "bug_hint": "Look carefully at what happens at the EXACT moment a window expires. There's an off-by-one or condition issue.",
        "feature_hint": "A sliding window typically uses a deque/list of timestamps and prunes entries older than the window.",

        "evaluation_rubric": {
            "bug_fixed":                {"weight": 0.30, "desc": "Did they actually fix the original bug?"},
            "feature_works":            {"weight": 0.30, "desc": "Does allow_request_sliding work correctly?"},
            "code_quality":             {"weight": 0.15, "desc": "Is the code clean, idiomatic, well-named?"},
            "ai_usage_quality":         {"weight": 0.15, "desc": "Did they use AI strategically? Or copy-paste blindly?"},
            "verification_discipline":  {"weight": 0.10, "desc": "Did they test their fix? Did they verify AI suggestions?"},
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Problem 2: Cache (alternative)
    # ─────────────────────────────────────────────────────────────
    "lru_cache_with_ttl": {
        "id": "lru_cache_with_ttl",
        "title": "Fix the Cache, then Add TTL Support",
        "difficulty": "medium",
        "time_limit_minutes": 30,
        "role_match": ["engineer", "backend", "ml"],

        "description": """
This is a basic LRU cache. It has a subtle bug, and you need to add TTL support.

## Part 1 — Fix the bug
The cache should evict the LEAST-recently-used item when full. But there's an issue
with how `get()` updates recency.

## Part 2 — Add the feature
Add an optional `ttl_seconds` parameter to `put()`. If set, the entry should
auto-expire after that many seconds. Expired entries should not be returned by `get()`.

## Constraints
- Python only. No external libraries.
- Capacity-based eviction (LRU) AND time-based eviction (TTL) must work together.
""",

        "starter_code": '''import time
from collections import OrderedDict

class LRUCache:
    """LRU cache with optional TTL. Has a bug somewhere."""

    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self.store = OrderedDict()  # key -> value

    def get(self, key):
        """Return value or None if missing. Bug: doesn't quite update LRU order."""
        if key in self.store:
            return self.store[key]
        return None

    def put(self, key, value, ttl_seconds: float = None):
        """Insert or update. Evict LRU if over capacity."""
        # TODO: support ttl_seconds — entries past their TTL should not be returned.
        if key in self.store:
            self.store[key] = value
            self.store.move_to_end(key)
        else:
            if len(self.store) >= self.capacity:
                self.store.popitem(last=False)
            self.store[key] = value
''',

        "test_cases_visible": [
            {
                "name": "Basic put + get",
                "code": '''c = LRUCache(3)
c.put("a", 1)
c.put("b", 2)
assert c.get("a") == 1
assert c.get("b") == 2
print("PASS: basic put/get")''',
            },
            {
                "name": "TTL parameter accepted",
                "code": '''c = LRUCache(3)
c.put("x", 1, ttl_seconds=10)
print("PASS: TTL parameter accepted")''',
            },
        ],

        "test_cases_hidden": [
            {
                "name": "LRU order with get",
                "code": '''c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
c.get("a")  # touch 'a' — should refresh recency
c.put("c", 3)  # 'b' should be evicted, not 'a'
assert c.get("a") == 1
assert c.get("b") is None
print("PASS: get refreshes recency")''',
            },
            {
                "name": "TTL expiry",
                "code": '''import time
c = LRUCache(3)
c.put("k", "v", ttl_seconds=0.5)
assert c.get("k") == "v"
time.sleep(0.7)
assert c.get("k") is None
print("PASS: TTL expiry works")''',
            },
        ],

        "bug_hint": "The `get()` method should not just return the value — it should also update something.",
        "feature_hint": "Store an expiry timestamp alongside each value. Check it on retrieval.",

        "evaluation_rubric": {
            "bug_fixed":               {"weight": 0.30, "desc": "Does get() now update LRU recency?"},
            "feature_works":           {"weight": 0.30, "desc": "Does TTL work correctly?"},
            "code_quality":            {"weight": 0.15, "desc": "Clean separation, no global state, etc."},
            "ai_usage_quality":        {"weight": 0.15, "desc": "Strategic AI use?"},
            "verification_discipline": {"weight": 0.10, "desc": "Did they verify edge cases?"},
        },
    },
}


def pick_problem(role_archetype: str = "engineer", seniority: str = "mid") -> dict:
    """Pick a problem matching the candidate's role."""
    # For now just return rate_limiter — extend later for role-based selection
    return PROBLEMS["rate_limiter"]


def get_problem(problem_id: str) -> dict:
    return PROBLEMS.get(problem_id, PROBLEMS["rate_limiter"])
