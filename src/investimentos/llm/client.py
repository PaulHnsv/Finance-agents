"""Provider-agnostic LLM client. Today targets GitHub Models (OpenAI-compatible)."""
from functools import lru_cache

from openai import OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from investimentos.config import get_settings


@lru_cache
def get_llm_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.github_token)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0, min=0, max=0),
    reraise=True,
)
def chat(messages: list[dict], *, model: str, max_tokens: int, temperature: float = 0.0) -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    content = response.choices[0].message.content
    return (content or "").strip()
