import json
import httpx
from typing import AsyncGenerator
from app.modules.providers.base import BaseProvider
from app.core.settings import settings

class GoogleGeminiProvider(BaseProvider):
    async def stream_chat(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        api_key = settings.google_key_value
        model_id = settings.gemini_model_id
        
        # Gemini expects a specific 'contents' format
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse"
        headers = {"x-goog-api-key": api_key}

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
            async with client.stream("POST", url, json={"contents": contents}, headers=headers) as response:
                if response.status_code != 200:
                    await response.aread()
                    error_text = f"[LLM_ERROR] Google Gemini API Error ({response.status_code}): {response.text}"
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': error_text}, 'finish_reason': 'error'}]})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                    
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            # Extract text from Gemini structure
                            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': text}, 'finish_reason': None}]})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                yield "data: [DONE]\n\n"
