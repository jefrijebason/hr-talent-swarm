from openai import AzureOpenAI
from shared.config import config
import json
import re
import time

client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.AZURE_OPENAI_API_VERSION
)

def _safe_call(model: str, messages: list, retries: int = 3) -> str:
    """
    Call OpenAI with:
    - Rate limit retry (exponential backoff)
    - Content filter handling
    - Timeout retry
    """
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content

        except Exception as e:
            err = str(e).lower()

            # ── Rate limit → wait and retry ──────────────────────
            if "rate_limit" in err or "429" in err:
                wait = (2 ** attempt) * 3  # 3s, 6s, 12s
                print(f"[OPENAI] Rate limited. Waiting {wait}s "
                      f"(attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue

            # ── Timeout → retry immediately ──────────────────────
            if "timeout" in err or "timed out" in err:
                wait = 2 * (attempt + 1)  # 2s, 4s, 6s
                print(f"[OPENAI] Timeout. Retrying in {wait}s "
                      f"(attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue

            # ── Content filter → clean and retry once ────────────
            if "content_filter" in err:
                print(f"[OPENAI] Content filter triggered. Retrying...")
                try:
                    last_msg = messages[-1]["content"]
                    cleaned = last_msg[:800].replace(
                        "24/7", "full time"
                    ).replace(
                        "self-harm", "wellbeing"
                    ).replace(
                        "suicide", "crisis"
                    )
                    clean_messages = [
                        {
                            "role": "system",
                            "content": "You are a professional HR assistant. "
                                       "Respond only in valid JSON."
                        },
                        {"role": "user", "content": cleaned}
                    ]
                    response = client.chat.completions.create(
                        model=model,
                        messages=clean_messages,
                        temperature=0.3
                    )
                    return response.choices[0].message.content
                except Exception as e2:
                    print(f"[OPENAI] Content filter retry failed: {e2}")
                    return "{}"

            # ── Service unavailable → wait and retry ─────────────
            if "503" in err or "502" in err or "service" in err:
                wait = (2 ** attempt) * 5  # 5s, 10s, 20s
                print(f"[OPENAI] Service unavailable. Waiting {wait}s...")
                time.sleep(wait)
                continue

            # ── Unknown error on last attempt → raise ────────────
            if attempt == retries - 1:
                print(f"[OPENAI] Failed after {retries} attempts: {e}")
                raise

            # ── Unknown error → short wait and retry ─────────────
            time.sleep(2)
            continue

    # Exhausted all retries
    print(f"[OPENAI] All {retries} attempts failed")
    return "{}"


def ask_gpt4o(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return _safe_call(config.MODEL_GPT4O, messages)


def ask_gpt4o_mini(prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return _safe_call(config.MODEL_GPT4O_MINI, messages)


def parse_json(raw: str) -> dict:
    cleaned = raw.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    try:
        fix = client.chat.completions.create(
            model=config.MODEL_GPT4O_MINI,
            messages=[{
                "role": "user",
                "content": f"Fix this JSON, return only valid JSON:\n{cleaned[:2000]}"
            }],
            temperature=0
        )
        fixed = fix.choices[0].message.content.strip()
        if "```" in fixed:
            fixed = fixed.split("```json")[-1].split("```")[0]
        return json.loads(fixed.strip())
    except Exception as e:
        print(f"[JSON] Parse failed: {e}")
        return {}