
import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

# Add backend to path so we can import llm_provider
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm_provider import LLMProvider

async def test_provider(provider_name, model_name):
    print(f"\n--- Testing Provider: {provider_name}, Model: {model_name} ---")
    
    # Override env vars for this test
    os.environ["LLM_PROVIDER"] = provider_name
    os.environ["LLM_MODEL"] = model_name
    
    # Re-instantiate provider (bypass singleton)
    try:
        provider = LLMProvider()
        
        # Manually force the properties since __init__ reads from env at instantiation
        # and os.environ change might propagate, but let's be safe.
        provider.provider = provider_name
        provider.model = model_name
        
        # Needed for OpenRouter specific setup in __init__
        if provider_name == "openrouter":
            provider.api_key = os.getenv("OPENROUTER_API_KEY")
            if not provider.api_key:
                print("SKIPPING: OPENROUTER_API_KEY not set")
                return

        response = await provider.generate(
            prompt="Say 'Hello World' and nothing else.",
            system_instruction="You are a test bot.",
            max_tokens=10
        )
        print(f"SUCCESS: {response}")
    except Exception as e:
        print(f"FAILED: {e}")

async def main():
    # Load env from backend/.env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)
    
    print(f"Loaded env from {env_path}")
    
    # Test 1: Configured Default (DeepSeek)
    await test_provider("openrouter", "deepseek/deepseek-chat")
    
    # Test 2: Gemini via OpenRouter (User said this works)
    # Note: Requires a valid model ID. "google/gemini-flash-1.5" is a common one.
    await test_provider("openrouter", "google/gemini-flash-1.5")
    
    # Test 3: Llama 3 via OpenRouter (Another common free/cheap one)
    await test_provider("openrouter", "meta-llama/llama-3-8b-instruct:free")

if __name__ == "__main__":
    asyncio.run(main())
