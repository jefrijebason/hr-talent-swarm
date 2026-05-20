from openai import AzureOpenAI
from shared.config import config
import json

# Single client used by all agents
client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.AZURE_OPENAI_API_VERSION
)

def ask_gpt4o(prompt: str, system: str = "") -> str:
    """
    Send a prompt to GPT-4o and get a response.
    Used by Evaluator and Orchestrator.
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
    Handles markdown code blocks.
    """
    cleaned = raw.strip()

    # Remove markdown code blocks if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())