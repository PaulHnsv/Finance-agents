from unittest.mock import MagicMock, patch
import pytest
from openai import RateLimitError
import httpx


def _mk_rate_limit_error() -> RateLimitError:
    req = httpx.Request("POST", "https://models.github.ai/inference/chat/completions")
    resp = httpx.Response(status_code=429, request=req)
    return RateLimitError("rate limited", response=resp, body=None)


def _mk_completion(text):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@patch("investimentos.llm.client.OpenAI")
def test_chat_returns_stripped_text(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client

    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()

    inst = MagicMock()
    inst.chat.completions.create.return_value = _mk_completion("  hello world  ")
    mock_openai_cls.return_value = inst

    out = llm_client.chat(
        messages=[{"role": "user", "content": "hi"}],
        model="openai/gpt-4o-mini",
        max_tokens=10,
    )

    assert out == "hello world"
    mock_openai_cls.assert_called_once_with(
        base_url="https://models.github.ai/inference",
        api_key="ghp-x",
    )
    inst.chat.completions.create.assert_called_once_with(
        model="openai/gpt-4o-mini",
        max_tokens=10,
        temperature=0.0,
        messages=[{"role": "user", "content": "hi"}],
    )


@patch("investimentos.llm.client.OpenAI")
def test_chat_handles_none_content(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client

    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()

    inst = MagicMock()
    inst.chat.completions.create.return_value = _mk_completion(None)
    mock_openai_cls.return_value = inst

    out = llm_client.chat(messages=[{"role": "user", "content": "x"}], model="m", max_tokens=1)
    assert out == ""


@patch("investimentos.llm.client.OpenAI")
def test_chat_retries_on_rate_limit(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client

    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()

    inst = MagicMock()
    inst.chat.completions.create.side_effect = [
        _mk_rate_limit_error(),
        _mk_completion("ok"),
    ]
    mock_openai_cls.return_value = inst

    out = llm_client.chat(messages=[{"role": "user", "content": "x"}], model="m", max_tokens=1)
    assert out == "ok"
    assert inst.chat.completions.create.call_count == 2


@patch("investimentos.llm.client.OpenAI")
def test_chat_gives_up_after_three_attempts(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client

    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()

    inst = MagicMock()
    inst.chat.completions.create.side_effect = _mk_rate_limit_error()
    mock_openai_cls.return_value = inst

    with pytest.raises(RateLimitError):
        llm_client.chat(messages=[{"role": "user", "content": "x"}], model="m", max_tokens=1)
    assert inst.chat.completions.create.call_count == 3


@patch("investimentos.llm.client.OpenAI")
def test_chat_passes_temperature_zero_by_default(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client
    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()
    inst = MagicMock()
    inst.chat.completions.create.return_value = _mk_completion("ok")
    mock_openai_cls.return_value = inst
    llm_client.chat(messages=[{"role": "user", "content": "x"}], model="m", max_tokens=10)
    kwargs = inst.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.0


@patch("investimentos.llm.client.OpenAI")
def test_chat_respects_explicit_temperature(mock_openai_cls, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-x")
    from investimentos.config import get_settings
    from investimentos.llm import client as llm_client
    get_settings.cache_clear()
    llm_client.get_llm_client.cache_clear()
    inst = MagicMock()
    inst.chat.completions.create.return_value = _mk_completion("ok")
    mock_openai_cls.return_value = inst
    llm_client.chat(messages=[{"role": "user", "content": "x"}], model="m", max_tokens=10, temperature=0.7)
    kwargs = inst.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.7
