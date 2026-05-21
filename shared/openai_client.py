from openai import AzureOpenAI
from shared.config import config
import json
import re

# Single client used by all agents
client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.AZURE_OPENAI_API_VERSION
)

def ask_gpt4o(prompt: str, system: str = "") -> str:
    """
    Send a prompt to GPT-4o and get a response.
    Used by Evaluator, Orchestrator, Interviewer.
    """
    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=config.MODEL_GPT4O,
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content

def ask_gpt4o_mini(prompt: str, system: str = "") -> str:
    """
    Send a prompt to GPT-4o Mini and get a response.
    Used by Screener and Communicator — cheaper.
    """
    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=config.MODEL_GPT4O_MINI,
        messages=messages,
        temperature=0.3
    )

    return response.choices[0].message.content

def parse_json(raw: str) -> dict:
    """
    Safely parse JSON from GPT response.
    Handles markdown code blocks and common JSON errors.
    """
    cleaned = raw.strip()

    # Remove markdown code blocks
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1]
        cleaned = cleaned.split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.split("```")[0]

    cleaned = cleaned.strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fix common issues — trailing commas
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)

    # Try again after fixing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Last resort — ask GPT-4o Mini to fix the JSON
    try:
        fix_response = client.chat.completions.create(
            model=config.MODEL_GPT4O_MINI,
            messages=[{
                "role": "user",
                "content": f"Fix this JSON and return only valid JSON, nothing else:\n{cleaned[:3000]}"
            }],
            temperature=0
        )
        fixed = fix_response.choices[0].message.content.strip()
        if "```" in fixed:
            fixed = fixed.split("```json")[-1].split("```")[0]
        return json.loads(fixed.strip())
    except Exception as e:
        print(f"[JSON] Could not parse JSON: {e}")
        return {}