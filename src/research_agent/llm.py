"""Thin LLM client. The only module that talks to the Gemini API."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client = None

MAX_RETRIES = 4
BASE_DELAY = 2.0


def _get_client():
    global _client
    if _client is not None:
        return _client

    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")

    from google import genai

    _client = genai.Client(api_key=api_key)
    return _client


def get_model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _handle_api_error(e: Exception, model: str) -> None:
    error_str = str(e)
    if "404" in error_str or "not_found" in error_str.lower():
        msg = (
            f"Model '{model}' was not found or is not accessible (404 Not Found).\n"
            f"Set GEMINI_MODEL in .env to a model active on your Google AI Studio account.\n"
            f'Check models with: python -c "from google import genai; '
            f'[print(m.name) for m in genai.Client().models.list()]"\n'
            f"Original API error: {e}"
        )
        raise RuntimeError(msg) from e


def call_llm(
    system_prompt: str,
    user_payload: str,
    temperature: float = 0.2,
) -> str:
    """Call the LLM and return the text response."""
    from google.genai import types

    client = _get_client()
    model = get_model_name()

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue
            _handle_api_error(e, model)
            raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries due to rate limiting")


def call_llm_structured(
    system_prompt: str,
    user_payload: str,
    schema: type[T],
    temperature: float = 0.1,
) -> T:
    """Call the LLM with JSON schema enforcement, return a parsed pydantic object."""
    from google.genai import types

    client = _get_client()
    model = get_model_name()

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            text = response.text
            data = json.loads(text)
            return schema.model_validate(data)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue
            _handle_api_error(e, model)
            raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries due to rate limiting")


def call_llm_json(
    system_prompt: str,
    user_payload: str,
    temperature: float = 0.1,
) -> dict | list:
    """Call the LLM requesting JSON output, return parsed JSON."""
    from google.genai import types

    client = _get_client()
    model = get_model_name()

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue
            _handle_api_error(e, model)
            raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries due to rate limiting")
