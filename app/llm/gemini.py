from typing import Any
import asyncio
from app.llm.base import (
    LLMNotConfiguredError,
    LLMProviderError,
    LLMTimeoutError,
    LLMRateLimitError,
)


class GeminiClient:
    """LLM client wrapping Google GenAI SDK with structured output, temperature tuning, and error mapping."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash",
        timeout_seconds: float = 20.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._client = None

    def _get_client(self):
        if not self.api_key:
            raise LLMNotConfiguredError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in your .env file."
            )

        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                raise LLMProviderError(f"Failed to initialize Google GenAI client: {e}") from e

        return self._client

    async def extract(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any] | None = None,
    ) -> str:
        client = self._get_client()
        prompt = payload.get("prompt", "")

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                from google.genai import types
                loop = asyncio.get_running_loop()

                def _call_gemini():
                    config_args: dict[str, Any] = {
                        "temperature": 0.0,  # Zero temperature for deterministic extraction
                    }
                    if schema:
                        config_args["response_mime_type"] = "application/json"
                        config_args["response_schema"] = schema

                    config = types.GenerateContentConfig(**config_args)

                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    )
                    return response.text

                result = await asyncio.wait_for(
                    loop.run_in_executor(None, _call_gemini),
                    timeout=self.timeout_seconds,
                )
                return result or "{}"

            except asyncio.TimeoutError:
                if attempt == max_retries:
                    raise LLMTimeoutError(f"Gemini API request timed out after {self.timeout_seconds}s")
                await asyncio.sleep(2.0)
            except LLMNotConfiguredError:
                raise
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = any(k in err_str for k in ("429", "quota", "rate limit", "resource_exhausted"))
                if is_rate_limit and attempt < max_retries:
                    await asyncio.sleep(3.0 * (attempt + 1))
                    continue
                if is_rate_limit:
                    raise LLMRateLimitError(f"Gemini rate limit exceeded: {e}") from e
                if any(k in err_str for k in ("api_key", "authentication", "unauthenticated")):
                    raise LLMNotConfiguredError(f"Invalid or unauthorized Gemini API key: {e}") from e
                raise LLMProviderError(f"Gemini provider error: {e}") from e

        return "{}"

    async def compose(self, payload: dict[str, Any]) -> str:
        client = self._get_client()
        prompt = payload.get("prompt", "")

        try:
            from google.genai import types
            loop = asyncio.get_running_loop()

            def _call_gemini():
                config = types.GenerateContentConfig(
                    temperature=0.7,
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                return response.text

            result = await asyncio.wait_for(
                loop.run_in_executor(None, _call_gemini),
                timeout=self.timeout_seconds,
            )
            return result or ""

        except asyncio.TimeoutError:
            raise LLMTimeoutError(f"Gemini API compose request timed out after {self.timeout_seconds}s")
        except LLMNotConfiguredError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
                # Return empty string to let ResponseComposer produce deterministic prompt without breaking the flow
                return ""
            raise LLMProviderError(f"Gemini provider error: {e}") from e
