from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel

from investimentos.llm.structured import chat_structured, StructuredOutputError


class Tiny(BaseModel):
    x: int
    y: str


def _mk_response(content: str) -> MagicMock:
    return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])


@patch("investimentos.llm.structured.get_llm_client")
def test_chat_structured_returns_validated_instance(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mk_response('{"x": 1, "y": "ok"}')
    mock_get_client.return_value = mock_client

    out = chat_structured(
        messages=[{"role": "user", "content": "x"}],
        response_schema=Tiny, model="m", max_tokens=100,
    )
    assert isinstance(out, Tiny)
    assert out.x == 1 and out.y == "ok"


@patch("investimentos.llm.structured.get_llm_client")
def test_chat_structured_retries_on_invalid_json_then_succeeds(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _mk_response("not json"),
        _mk_response('{"x": 2, "y": "fixed"}'),
    ]
    mock_get_client.return_value = mock_client

    out = chat_structured(
        messages=[{"role": "user", "content": "x"}],
        response_schema=Tiny, model="m", max_tokens=100,
    )
    assert out.x == 2
    assert mock_client.chat.completions.create.call_count == 2


@patch("investimentos.llm.structured.get_llm_client")
def test_chat_structured_raises_after_two_failures(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mk_response("still not json")
    mock_get_client.return_value = mock_client

    with pytest.raises(StructuredOutputError):
        chat_structured(
            messages=[{"role": "user", "content": "x"}],
            response_schema=Tiny, model="m", max_tokens=100,
        )


@patch("investimentos.llm.structured.get_llm_client")
def test_chat_structured_strips_markdown_fences(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mk_response(
        "```json\n{\"x\": 3, \"y\": \"a\"}\n```"
    )
    mock_get_client.return_value = mock_client

    out = chat_structured(
        messages=[{"role": "user", "content": "x"}],
        response_schema=Tiny, model="m", max_tokens=100,
    )
    assert out.x == 3
