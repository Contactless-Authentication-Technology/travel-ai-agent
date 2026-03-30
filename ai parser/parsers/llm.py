import json
import os
from typing import Any, Dict

from openai import OpenAI, OpenAIError


class LLMStructuredOutputError(Exception):
    """Raised when LLM structured output cannot be parsed or validated."""


def _get_openai_client() -> OpenAI:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key == "sk-..." or api_key.endswith("..."):
        raise LLMStructuredOutputError("OPENAI_API_KEY is not set in environment.")
    return OpenAI(api_key=api_key)


def _call_llm_structured(message: str) -> Dict[str, Any]:
    client = _get_openai_client()
    model = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o-mini")

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a travel plan parser. Output ONLY a JSON object (no prose). "
                        "If unknown, use null/empty objects."
                    ),
                },
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
        )
    except OpenAIError as exc:
        raise LLMStructuredOutputError(f"OpenAI request failed: {exc}") from exc

    content = resp.choices[0].message.content
    if not isinstance(content, str):
        raise LLMStructuredOutputError("LLM response content is not a string JSON.")

    try:
        data = json.loads(content)
    except Exception as exc:
        raise LLMStructuredOutputError("Failed to json.loads() LLM output.") from exc

    if not isinstance(data, dict):
        raise LLMStructuredOutputError("LLM output is not a JSON object.")
    return data
