import json
import logging
import httpx
from typing import Dict, Optional
from andromancer import config as cfg

logger = logging.getLogger("AndroMancer.LLM")

class LLMError(Exception):
    pass

class AsyncLLMClient:
    """Async client for LLM (GROQ/OpenAI)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or cfg.GROQ_API_KEY
        self.model = model or cfg.MODEL_NAME

    async def complete_chat(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> dict:
        if not self.api_key:
            raise LLMError("API Key not found. Please set it in .env or settings.py")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=timeout
                )

            if resp.status_code >= 400:
                raise LLMError(f"LLM request failed: {resp.status_code} {resp.text}")

            body = resp.json()
            content = body["choices"][0]["message"]["content"]

            if isinstance(content, str):
                return json.loads(content)
            elif isinstance(content, dict):
                return content
            else:
                raise LLMError("Unexpected LLM content format")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise LLMError(f"Failed to call LLM: {str(e)}")

    async def complete_text(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> str:
        """Simple text completion without JSON format enforcement"""
        if not self.api_key:
            raise LLMError("API Key not found")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7
                    },
                    timeout=timeout
                )

            if resp.status_code >= 400:
                raise LLMError(f"LLM request failed: {resp.status_code}")

            body = resp.json()
            return body["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM text call failed: {e}")
            return f"Error: {str(e)}"
