from fastapi import APIRouter, status, Depends
from datetime import datetime, timezone

from app.config import settings
from app.llm.base import LLMClient
from app.llm.mock import MockLLMClient
from app.llm.gemini import GeminiClient
from app.services.session_store import session_store
from app.services.conversation import ConversationService
from app.docgen.renderer import render_wishes_document
from app.domain.planner import get_missing_fields, is_state_complete
from app.api.schemas import (
    CreateSessionResponse,
    SendMessageRequest,
    SessionDetailResponse,
    MessageTurnResponse,
    DocumentResponse,
)
from app.api.errors import session_not_found

router = APIRouter(prefix="/api", tags=["Intake"])


def get_llm_client() -> LLMClient:
    """Dependency provider for LLM client based on application configuration."""
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiClient(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
        )
    return MockLLMClient()


def get_conversation_service(llm_client: LLMClient = Depends(get_llm_client)) -> ConversationService:
    return ConversationService(llm_client=llm_client)


@router.get("/health")
async def health_check():
    """Check application health and LLM provider configuration status."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "llm_configured": settings.is_llm_configured,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session():
    """Creates a new intake session."""
    session = await session_store.create()
    return CreateSessionResponse(
        session_id=session.id,
        created_at=session.created_at.isoformat(),
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """Retrieves current session state, messages, and rendered document."""
    session = await session_store.get(session_id)
    if not session:
        raise session_not_found(session_id)

    doc = render_wishes_document(session.state, has_pending_clarification=bool(session.pending_clarification))
    missing = get_missing_fields(session.state)
    complete = is_state_complete(session.state, has_pending_clarification=bool(session.pending_clarification))

    return SessionDetailResponse(
        session_id=session.id,
        state=session.state,
        messages=session.messages,
        changes=session.changes,
        pending_clarification=session.pending_clarification,
        missing_fields=missing,
        is_complete=complete,
        document=DocumentResponse(
            title=doc.title,
            text=doc.text,
            is_complete=doc.is_complete,
            missing_fields=doc.missing_fields,
        ),
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageTurnResponse)
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    conv_service: ConversationService = Depends(get_conversation_service),
):
    """Processes a user message turn within a per-session lock."""
    # Serialize mutations using per-session concurrency lock
    async with session_store.lock(session_id):
        session = await session_store.get(session_id)
        if not session:
            raise session_not_found(session_id)

        updated_session, assistant_message, changes = await conv_service.process_user_turn(
            session=session,
            user_message=payload.message,
        )

        await session_store.save(updated_session)

        doc = render_wishes_document(
            updated_session.state,
            has_pending_clarification=bool(updated_session.pending_clarification),
        )
        missing = get_missing_fields(updated_session.state)
        complete = is_state_complete(
            updated_session.state,
            has_pending_clarification=bool(updated_session.pending_clarification),
        )

        return MessageTurnResponse(
            session_id=updated_session.id,
            assistant_message=assistant_message,
            state=updated_session.state,
            changes=changes,
            pending_clarification=updated_session.pending_clarification,
            missing_fields=missing,
            is_complete=complete,
            document=DocumentResponse(
                title=doc.title,
                text=doc.text,
                is_complete=doc.is_complete,
                missing_fields=doc.missing_fields,
            ),
        )


@router.get("/sessions/{session_id}/document", response_model=DocumentResponse)
async def get_document(session_id: str):
    """Retrieves current draft Personal Wishes Document."""
    session = await session_store.get(session_id)
    if not session:
        raise session_not_found(session_id)

    doc = render_wishes_document(
        session.state,
        has_pending_clarification=bool(session.pending_clarification),
    )
    return DocumentResponse(
        title=doc.title,
        text=doc.text,
        is_complete=doc.is_complete,
        missing_fields=doc.missing_fields,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Deletes/resets an intake session."""
    deleted = await session_store.delete(session_id)
    if not deleted:
        raise session_not_found(session_id)
    return {"message": f"Session '{session_id}' successfully deleted.", "session_id": session_id}
