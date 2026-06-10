import hmac
import hashlib
from shared.config import config

def generate_token(action: str, resource_id: str) -> str:
    """Generate a secure HMAC token for an action + resource."""
    key     = config.ACTION_SECRET.encode()
    message = f"{action}:{resource_id}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()[:32]

def verify_token(action: str, resource_id: str, token: str) -> bool:
    """Verify a token is valid for this action + resource."""
    if not token:
        return False
    expected = generate_token(action, resource_id)
    return hmac.compare_digest(expected, token)