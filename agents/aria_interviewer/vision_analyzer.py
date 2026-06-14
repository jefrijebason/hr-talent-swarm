"""
agents/aria_interviewer/vision_analyzer.py

GPT-4o Vision analyzer for screen-share frames during an AI interview.

Workflow per frame:
  1. Compute a perceptual hash of the frame.
  2. If the hash is close to the last analyzed frame, SKIP (saves ~70% of vision cost).
  3. Otherwise call GPT-4o Vision with role + claim context.
  4. Return:
        - description     : what's on screen
        - relevance       : how relevant to the claim being demoed
        - follow_up_q     : optional contextual question ARIA can ask
        - anti_cheat_flags: list of detected concerns (browser tabs, AI tool windows, etc.)

Cost control: hard-cap to 30 vision calls per session.
"""

import os
import json
import hashlib
import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from openai import AzureOpenAI

logger = logging.getLogger(__name__)

_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        )
    return _client


def _gpt4o() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O") or os.getenv("MODEL_GPT4O") or "gpt-4o"


# Cap to keep cost predictable
MAX_VISION_CALLS_PER_SESSION = 30


# ════════════════════════════════════════════════════════════════════════
# Perceptual hash (very simple — sufficient to skip identical frames)
# ════════════════════════════════════════════════════════════════════════
def _perceptual_hash(image_bytes: bytes) -> str:
    """
    Tiny PIL-based pHash. Not the world's best, but good enough to detect
    'this is the same screen as before'. Falls back to MD5 if PIL unavailable.
    """
    try:
        from PIL import Image
        img = Image.open(BytesIO(image_bytes)).convert("L").resize((16, 16))
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        # 256 bits packed
        return f"{int(bits, 2):064x}"
    except Exception:
        return hashlib.md5(image_bytes).hexdigest()


def _hashes_similar(h1: str, h2: str, max_distance: int = 6) -> bool:
    """Hamming distance over hex hashes — close enough = same frame."""
    if not h1 or not h2 or len(h1) != len(h2):
        return False
    try:
        a = int(h1, 16); b = int(h2, 16)
        return bin(a ^ b).count("1") <= max_distance
    except Exception:
        return h1 == h2


# ════════════════════════════════════════════════════════════════════════
# Main entry
# ════════════════════════════════════════════════════════════════════════
def analyze_screen_frame(
    *,
    image_bytes: bytes,
    candidate_name: str,
    role: str,
    project_claim: str,
    last_hash: Optional[str] = None,
    calls_so_far: int = 0,
) -> Dict[str, Any]:
    """
    Analyze a single screenshot frame.

    Returns:
      {
        "skipped":           bool,
        "phash":             str,
        "description":       str,
        "relevance":         "high"|"medium"|"low"|"unknown",
        "follow_up_question": str | "",
        "anti_cheat_flags":  [{"type": "...", "severity": "low"|"medium"|"high", "detail": "..."}],
      }
    """
    phash = _perceptual_hash(image_bytes)

    # Skip if duplicate
    if last_hash and _hashes_similar(phash, last_hash):
        return _skipped_result(phash, reason="duplicate frame")

    if calls_so_far >= MAX_VISION_CALLS_PER_SESSION:
        return _skipped_result(phash, reason="vision call cap reached")

    # Encode image as data URL
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64}"

    system_prompt = """You are ARIA's vision analyzer. The candidate is demonstrating their work
via screen-share during an AI interview. Look at the frame and report.

Output JSON with this schema:
{
  "description":        "<one sentence: what's on screen>",
  "relevance":          "high|medium|low|unknown",
  "follow_up_question": "<optional contextual question, or empty string>",
  "anti_cheat_flags":   [
    {"type": "<see below>", "severity": "low|medium|high", "detail": "<one sentence>"}
  ]
}

ANTI-CHEAT FLAG TYPES (only flag if confidently present):
- "ai_assistant_visible"   : ChatGPT, Claude, Copilot, Gemini, etc. window or tab visible
- "second_screen_likely"   : signs of cursor leaving frame, or candidate looking offscreen
- "static_screen"          : the candidate is talking but screen hasn't changed at all
- "plagiarized_source"     : visible code or content that appears copied from a known tutorial/source
- "off_topic"              : screen content unrelated to what they claim to be demoing
- "private_info_visible"   : passwords, credentials, customer PII clearly visible (warn HR)

FOLLOW-UP QUESTION RULES:
- Be specific to what you see. Reference a UI element, metric, or piece of code.
- Don't ask generic things like "tell me more". Ask "what does that chart represent?"
- Return empty string if nothing interesting to ask.

Be conservative. Empty arrays / empty strings beat false positives.
"""

    user_prompt = f"""
Candidate: {candidate_name}
Role: {role}
Project they're demoing (their resume claim): {project_claim}

Analyze the frame and respond with JSON.
"""

    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=_gpt4o(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text",      "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                ]},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500,
        )
        out = json.loads(resp.choices[0].message.content or "{}")
        return {
            "skipped":           False,
            "phash":             phash,
            "description":       out.get("description", ""),
            "relevance":         out.get("relevance", "unknown"),
            "follow_up_question": out.get("follow_up_question", ""),
            "anti_cheat_flags":  out.get("anti_cheat_flags", []),
        }

    except Exception as e:
        logger.error(f"[ARIA-Vision] frame analysis failed: {e}", exc_info=True)
        return {
            "skipped":           False,
            "phash":             phash,
            "description":       "",
            "relevance":         "unknown",
            "follow_up_question": "",
            "anti_cheat_flags":  [],
            "_error":            str(e),
        }


def _skipped_result(phash: str, reason: str) -> Dict[str, Any]:
    return {
        "skipped":           True,
        "phash":             phash,
        "description":       "",
        "relevance":         "unknown",
        "follow_up_question": "",
        "anti_cheat_flags":  [],
        "_skip_reason":      reason,
    }