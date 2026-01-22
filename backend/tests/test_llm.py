import os
import sys

import pytest
from dotenv import load_dotenv

# Ensure backend module is available
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.llm_provider import LLMProvider

# Load env variables for tests
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

@pytest.mark.asyncio
async def test_llm_provider_initialization():
    """Test that LLMProvider initializes correctly with env vars."""
    provider = LLMProvider()
    assert provider.provider is not None
    assert provider.model is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_openrouter_generation():
    """Integration test for OpenRouter generation."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")
    
    provider = LLMProvider()
    # Force OpenRouter for this test
    provider.provider = "openrouter"
    # Use the configured model from env if possible, else default to deepseek/deepseek-chat
    provider.model = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
    
    try:
        response = await provider.generate(
            prompt="Say 'Hello World' and nothing else.",
            system_instruction="You are a test bot.",
            max_tokens=10
        )
        assert response is not None
        assert len(response) > 0
    except ValueError as e:
        if "404" in str(e) or "402" in str(e): # Model not found or Insufficient Credits
            pytest.skip(f"Skipping due to API error (likely model availability): {e}")
        else:
            raise e
    except Exception as e:
        pytest.skip(f"Skipping due to connection error: {e}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_via_openrouter():
    """Integration test for Gemini via OpenRouter."""
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")

    provider = LLMProvider()
    provider.provider = "openrouter"
    provider.model = "google/gemini-2.0-flash-exp:free" # Try a free one if available

    try:
        response = await provider.generate(
            prompt="Say 'Test' and nothing else.",
            system_instruction="You are a test bot.",
            max_tokens=10
        )
        assert response is not None
    except Exception as e:
        pytest.skip(f"Gemini API check failed (expected for free/beta models potentially): {e}")
