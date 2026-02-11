import asyncio
import json
import logging
import re
import httpx
from typing import Dict, Optional, Any
from andromancer import config as cfg

logger = logging.getLogger("AndroMancer.LLM")

class LLMError(Exception):
    pass

class AsyncLLMClient:
    """Async client for LLM (GROQ/OpenAI) with retry logic"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or cfg.GROQ_API_KEY
        self.model = model or cfg.MODEL_NAME

    async def _request_with_retry(self, payload: Dict[str, Any], timeout: float = 30.0, max_retries: int = 3) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                        timeout=timeout
                    )

                    if resp.status_code == 429:
                        wait_time = 2 ** (attempt + 1)
                        try:
                            error_msg = resp.json().get("error", {}).get("message", "")
                            match = re.search(r"try again in ([\d\.]+)s", error_msg)
                            if match:
                                wait_time = float(match.group(1)) + 0.1
                        except:
                            pass

                        logger.warning(f"Rate limit reached. Retrying in {wait_time:.2f}s... (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue

                    if resp.status_code >= 500:
                        wait_time = 2 ** (attempt + 1)
                        logger.warning(f"Server error {resp.status_code}. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue

                    return resp
                except (httpx.RequestError, asyncio.TimeoutError) as e:
                    if attempt == max_retries - 1:
                        raise e
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Network error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            # Final attempt if loop finished without returning
            return await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=timeout
            )

    async def complete_chat(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> dict:
        if not self.api_key:
            raise LLMError("API Key not found. Please set it in .env or settings.py")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        try:
            resp = await self._request_with_retry(payload, timeout=timeout)

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
            logger.error(f"LLM call failed after retries: {e}")
            raise LLMError(f"Failed to call LLM: {str(e)}")

    async def complete_text(self, system_prompt: str, user_prompt: str, timeout: float = 30.0) -> str:
        """Simple text completion without JSON format enforcement"""
        if not self.api_key:
            raise LLMError("API Key not found")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        try:
            resp = await self._request_with_retry(payload, timeout=timeout)

            if resp.status_code >= 400:
                raise LLMError(f"LLM request failed: {resp.status_code}")

            body = resp.json()
            return body["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM text call failed: {e}")
            return f"Error: {str(e)}"
