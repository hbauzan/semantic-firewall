import json
import httpx
from typing import AsyncGenerator
from app.modules.providers.base import BaseProvider
from app.core.settings import settings


class OllamaProvider(BaseProvider):
    async def stream_chat(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        prompt = messages[-1]["content"]
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': data.get('response', '')}, 'finish_reason': None}]})}\n\n"
                yield "data: [DONE]\n\n"
