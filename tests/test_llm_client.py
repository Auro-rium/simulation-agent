import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from llm.llm_client import LLMClient

# Mock Groq classes
@pytest.fixture
def mock_groq():
    with patch("llm.llm_client.AsyncGroq") as MockClient:
        mock_instance = AsyncMock()
        MockClient.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def client(mock_groq):
    with patch("os.environ.get", return_value="dummy_key"), \
         patch("llm.llm_client.LLMClient._read_cache", new_callable=AsyncMock) as mock_read:
        
        mock_read.return_value = None # Force no cache
        
        yield LLMClient()

@pytest.mark.asyncio
async def test_groq_mapping(client, mock_groq):
    """Verify Model Mapping."""
    mock_chat = AsyncMock()
    mock_groq.chat.completions.create = mock_chat
    
    mock_response = MagicMock()
    mock_response.choices[0].finish_reason = "stop"
    mock_response.choices[0].message.content = "Response"
    mock_chat.return_value = mock_response
    
    # helper for clean testing
    async def run_gen(internal_model):
        await client.generate("Hi", model=internal_model)
        call_kwargs = mock_chat.call_args.kwargs
        return call_kwargs["model"]

    # Test Pro mapping (Now Identity or Default)
    # The client no longer maps 'gemini', so we test the new constants directly
    assert await run_gen(LLMClient.MODEL_REASONING) == "openai/gpt-oss-120b"
    assert await run_gen(LLMClient.MODEL_FAST) == "openai/gpt-oss-20b"

@pytest.mark.asyncio
async def test_structured_output_json_mode(client, mock_groq):
    """Verify JSON mode is forced."""
    mock_chat = AsyncMock()
    mock_groq.chat.completions.create = mock_chat
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"foo": "bar"}'
    mock_chat.return_value = mock_response
    
    await client.generate_structured_output("Prompt", {"type": "obj"})
    
    call_kwargs = mock_chat.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
    assert call_kwargs["temperature"] == 0.1
