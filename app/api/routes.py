from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone
from app.config import settings

router = APIRouter(prefix="/api", tags=["System"])


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    llm_provider: str
    llm_configured: bool
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health and LLM provider configuration status."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_configured=settings.is_llm_configured,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
