import json
import httpx
from typing import AsyncGenerator
from app.modules.providers.base import BaseProvider
from app.core.settings import settings


class OpenAIProvider(BaseProvider):
    async def stream_chat(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        api_key = settings.openai_key_value
        if not api_key:
            yield "data: {\"choices\": [{\"delta\": {\"content\": \"🔴 [LLM ERROR] Missing OpenAI API Key\"}, \"finish_reason\": \"error\"}]}\n\n"
            yield "data: [DONE]\n\n"
            return

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    await response.aread()
                    error_text = f"🔴 [LLM ERROR] OpenAI API Error ({response.status_code}): {response.text}"
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': error_text}, 'finish_reason': 'error'}]})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n"
