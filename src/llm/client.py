"""
OpenAI client singleton for the Legal Knowledge Recommendation Engine.

Configuration via environment variables:
    OPENAI_API_KEY    — required for all LLM features
    OPENAI_MODEL      — default "gpt-4o-mini"
    OPENAI_MAX_TOKENS — default 2048

Graceful degradation:
    If OPENAI_API_KEY is absent, is_available() returns False and callers
    fall back to the deterministic ReasoningEngine in src/graphrag/reasoning.py.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_client = None
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_MAX_TOKENS = 2048


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Set it in .env or as an environment variable to enable LLM features."
            )
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.0.0"
            )
        _client = OpenAI(api_key=api_key)
    return _client


def is_available() -> bool:
    """Return True if OPENAI_API_KEY is set and the openai package is installed."""
    if not os.environ.get("OPENAI_API_KEY"):
        return False
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL)


def get_max_tokens() -> int:
    return int(os.environ.get("OPENAI_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)))


def chat_complete(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.2,
    response_format: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Simple synchronous chat completion.
    Returns the assistant message string, or None on any failure.
    """
    try:
        client = _get_client()
        kwargs: Dict[str, Any] = {
            "model": model or get_model(),
            "messages": messages,
            "max_tokens": max_tokens or get_max_tokens(),
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("chat_complete failed: %s", exc)
        return None


def chat_complete_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.1,
    tool_choice: str = "auto",
) -> Optional[Any]:
    """
    Chat completion with OpenAI tool/function calling.
    Returns the raw ChatCompletion response object, or None on failure.
    The caller inspects resp.choices[0].message.tool_calls to dispatch tools.
    """
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=model or get_model(),
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens or get_max_tokens(),
            temperature=temperature,
        )
        return resp
    except Exception as exc:
        logger.warning("chat_complete_with_tools failed: %s", exc)
        return None


class LLMClient:
    """
    Wrapper around the OpenAI client.
    Returns dict-format responses compatible with the orchestrator's tool-calling loop.
    """

    def __init__(self, client, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def chat_complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
    ) -> Optional[Dict[str, Any]]:
        """
        Call the OpenAI chat-completions API with tool definitions.

        Returns a dict: {"content": str, "tool_calls": [...]} or None on failure.
        tool_calls entries are dicts: {"id", "type", "function": {"name", "arguments"}}.
        """
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                max_tokens=self._max_tokens,
                temperature=0.1,
            )
            msg = resp.choices[0].message
            result: Dict[str, Any] = {"content": msg.content or ""}
            if msg.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            return result
        except Exception as exc:
            logger.warning("LLMClient.chat_complete_with_tools failed: %s", exc)
            return None


def get_llm_client() -> Optional[LLMClient]:
    """Return an LLMClient if OPENAI_API_KEY is set and openai is installed, else None."""
    if not is_available():
        return None
    try:
        client = _get_client()
        return LLMClient(client, get_model(), get_max_tokens())
    except Exception as exc:
        logger.warning("get_llm_client failed: %s", exc)
        return None


def embed_with_openai(text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    """
    Generate an embedding via OpenAI (1536-dim for text-embedding-3-small).
    Only used when explicitly requested — the default embedding pipeline uses
    the local sentence-transformer model (384-dim).
    """
    try:
        client = _get_client()
        resp = client.embeddings.create(input=[text], model=model)
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("embed_with_openai failed: %s", exc)
        return None
