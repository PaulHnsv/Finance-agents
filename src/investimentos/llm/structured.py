"""Structured LLM output — Pydantic-validated chat with repair retry."""
from __future__ import annotations
import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from investimentos.llm.client import get_llm_client

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    pass


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _extract_json(text: str) -> str:
    return _FENCE_RE.sub("", text or "").strip()


def chat_structured(
    *,
    messages: list[dict],
    response_schema: type[T],
    model: str,
    max_tokens: int,
    temperature: float = 0.0,
) -> T:
    """Call LLM and validate against response_schema. One repair retry on failure."""
    client = get_llm_client()
    schema_json = json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
    system_msg = {
        "role": "system",
        "content": (
            "You MUST respond with a single JSON object that conforms exactly to this JSON schema. "
            "Do not include any prose, markdown fences, or comments. Schema:\n" + schema_json
        ),
    }
    conversation = [system_msg, *messages]

    last_err: Exception | None = None
    for _ in range(2):
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=conversation,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        candidate = _extract_json(raw)
        try:
            return response_schema.model_validate_json(candidate)
        except (ValidationError, ValueError) as e:
            last_err = e
            conversation = [
                *conversation,
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "Your previous response failed validation with this error:\n"
                        f"{e}\n"
                        "Respond again with ONLY a valid JSON object matching the schema."
                    ),
                },
            ]
    raise StructuredOutputError(f"LLM failed to produce valid output: {last_err}")
