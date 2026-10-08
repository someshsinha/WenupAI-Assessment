from typing import Protocol, Any, runtime_checkable


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMNotConfiguredError(LLMError):
    """Raised when LLM API credentials or configuration is missing."""
    pass


class LLMProviderError(LLMError):
    """Raised when the LLM provider fails or returns network/upstream errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when the LLM provider times out."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when the LLM provider rate limits requests."""
    pass


class LLMBadResponseError(LLMError):
    """Raised when the LLM returns unparseable or schema-invalid output."""
    pass


@runtime_checkable
class LLMClient(Protocol):
    """Abstract protocol for LLM providers."""

    async def extract(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any] | None = None,
    ) -> str:
        """Extracts structured operations JSON string from user turn."""
        ...

    async def compose(
        self,
        payload: dict[str, Any],
    ) -> str:
        """Composes a natural-language assistant response string."""
        ...
