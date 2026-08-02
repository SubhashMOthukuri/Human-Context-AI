import json

import openai
from openai import OpenAI

from app.config import settings


class LLMNotConfigured(Exception):
    pass


class LLMRequestFailed(Exception):
    pass


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise LLMNotConfigured(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=settings.openai_api_key)


def generate_json(
    system_prompt: str, user_prompt: str, max_tokens: int = 4096, temperature: float = 0.4
) -> dict:
    try:
        completion = _client().chat.completions.create(
            model=settings.openai_model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except openai.AuthenticationError as exc:
        raise LLMRequestFailed("OpenAI rejected this API key — check it's correct.") from exc
    except openai.RateLimitError as exc:
        raise LLMRequestFailed(
            "OpenAI account has no available quota (insufficient_quota). Add a payment "
            "method / credits at https://platform.openai.com/account/billing."
        ) from exc
    except openai.APIError as exc:
        raise LLMRequestFailed(f"OpenAI API error: {exc}") from exc

    text = completion.choices[0].message.content or ""
    return _extract_json(text)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {text[:300]!r}")
    return json.loads(text[start : end + 1])
