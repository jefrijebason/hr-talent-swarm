import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# Connect directly to Azure OpenAI
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Test connection first
print("Testing Azure OpenAI connection...")

# Create a simple test
response = client.chat.completions.create(
    model=os.getenv("MODEL_GPT4O"),
    messages=[
        {"role": "user", "content": "Say hello in one word"}
    ]
)

print(f"✓ Connection working!")
print(f"Response: {response.choices[0].message.content}")

# Now create vector store
print("\nCreating vector store...")
vector_store = client.beta.vector_stores.create(
    name="hr-resumes-store"
)

print(f"✓ Vector store created!")
print(f"ID: {vector_store.id}")
print(f"\nAdd to .env:")
print(f"FOUNDRY_VECTOR_STORE_ID={vector_store.id}")