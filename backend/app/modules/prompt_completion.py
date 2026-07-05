"""Non-streaming LLM prompt completion for dataset generation."""
from __future__ import annotations

import logging

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)


def complete_prompt(prompt: str, provider: str | None = None, model: str | None = None) -> str | None:
    """Run a single completion; returns None if provider unavailable or on error."""
    provider = provider or settings.upstream_provider
    try:
        if provider == "ollama":
            return _complete_ollama(prompt, model or settings.ollama_model)
        if provider == "openai" and settings.openai_key_value:
            return _complete_openai(prompt, model or settings.openai_model)
        if provider == "anthropic" and settings.anthropic_key_value:
            return _complete_anthropic(prompt, model or settings.anthropic_model)
        if provider == "google" and settings.google_key_value:
            return _complete_google(prompt, model or settings.gemini_model_id)
        if provider == "groq" and settings.groq_key_value:
            return _complete_groq(prompt, model or settings.groq_model)
    except Exception as e:
        logger.warning("LLM completion failed (%s): %s", provider, e)
    return None


def _complete_ollama(prompt: str, model: str) -> str | None:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        if resp.status_code != 200:
            logger.warning("Ollama generate HTTP %s", resp.status_code)
            return None
        return resp.json().get("response", "").strip() or None


def _complete_openai(prompt: str, model: str) -> str | None:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_key_value}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        if resp.status_code != 200:
            logger.warning("OpenAI HTTP %s", resp.status_code)
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip() or None


def _complete_anthropic(prompt: str, model: str) -> str | None:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_key_value,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        if resp.status_code != 200:
            logger.warning("Anthropic HTTP %s", resp.status_code)
            return None
        data = resp.json()
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return text.strip() or None


def _complete_google(prompt: str, model: str) -> str | None:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.google_key_value}"
    )
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        if resp.status_code != 200:
            logger.warning("Google Gemini HTTP %s", resp.status_code)
            return None
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        return text.strip() or None


def _complete_groq(prompt: str, model: str) -> str | None:
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_key_value}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
        )
        if resp.status_code != 200:
            logger.warning("Groq HTTP %s", resp.status_code)
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip() or None
