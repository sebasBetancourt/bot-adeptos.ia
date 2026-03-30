"""Quick test for Haiku 4.5 model ID."""
from anthropic import Anthropic
import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=key)

models = [
    "claude-haiku-4-5-20250514",
    "claude-3-5-haiku-20241022",
    "claude-sonnet-4-20250514",
]

for m in models:
    try:
        print(f"Testing {m}...", end=" ")
        r = client.messages.create(
            model=m, max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}]
        )
        print(f"✅ {r.content[0].text}")
        break
    except Exception as e:
        print(f"❌ {str(e)[:60]}")
