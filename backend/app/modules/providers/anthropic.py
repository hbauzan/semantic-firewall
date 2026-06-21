import json
import httpx
from typing import AsyncGenerator
from app.modules.providers.base import BaseProvider
from app.core.settings import settings


class AnthropicProvider(BaseProvider):
    async def stream_chat(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        api_key = settings.anthropic_key_value
        if not api_key:
            yield "data: {\"choices\": [{\"delta\": {\"content\": \"🔴 [LLM ERROR] Missing Anthropic API Key\"}, \"finish_reason\": \"error\"}]}\n\n"
            yield "data: [DONE]\n\n"
            return

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        system_prompt = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt += m["content"] + "\n"
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt.strip()

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    await response.aread()
                    error_text = f"🔴 [LLM ERROR] Anthropic API Error ({response.status_code}): {response.text}"
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': error_text}, 'finish_reason': 'error'}]})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break

                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {}).get("text", "")
                                if delta:
                                    yield f"data: {json.dumps({'choices': [{'delta': {'content': delta}, 'finish_reason': None}]})}\n\n"
                            elif data.get("type") == "message_stop":
                                yield "data: [DONE]\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
