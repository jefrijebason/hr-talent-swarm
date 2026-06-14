import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Foundry
    AZURE_AI_FOUNDRY_ENDPOINT   = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    AZURE_AI_FOUNDRY_KEY        = os.getenv("AZURE_AI_FOUNDRY_KEY")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT       = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY        = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION    = os.getenv("AZURE_OPENAI_API_VERSION")
    MODEL_GPT4O                 = os.getenv("MODEL_GPT4O", "gpt-4o")
    MODEL_GPT4O_MINI            = os.getenv("MODEL_GPT4O_MINI", "gpt-4o-mini")

    # Cosmos DB
    COSMOS_ENDPOINT             = os.getenv("COSMOS_ENDPOINT")
    COSMOS_KEY                  = os.getenv("COSMOS_KEY")
    COSMOS_DATABASE             = os.getenv("COSMOS_DATABASE", "hr-swarm")

    # Service Bus
    SERVICE_BUS_CONNECTION      = os.getenv("SERVICE_BUS_CONNECTION")

    # Blob Storage
    BLOB_CONNECTION             = os.getenv("BLOB_CONNECTION")
    BLOB_CONTAINER              = os.getenv("BLOB_CONTAINER", "resumes")

    # Azure Communication Services
    ACS_CONNECTION              = os.getenv("ACS_CONNECTION")
    ACS_EMAIL_SENDER            = os.getenv("ACS_EMAIL_SENDER")

    # Graph API
    GRAPH_TENANT_ID             = os.getenv("GRAPH_TENANT_ID")
    GRAPH_CLIENT_ID             = os.getenv("GRAPH_CLIENT_ID")
    GRAPH_CLIENT_SECRET         = os.getenv("GRAPH_CLIENT_SECRET")

    # Judge0
    JUDGE0_URL                  = os.getenv("JUDGE0_URL", "http://localhost:2358")

    # Demo mode
    DEMO_MODE                   = os.getenv("DEMO_MODE", "false").lower() == "true"

config = Config()
ACTION_SECRET = os.getenv("ACTION_SECRET", "hr-swarm-secret-2026")
PUBLIC_URL: str = os.getenv("PUBLIC_URL", "http://localhost:8000")
ACTION_SECRET = os.getenv("ACTION_SECRET", "hr-swarm-demo-secret-key-2026")