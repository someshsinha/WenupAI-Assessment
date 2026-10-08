from typing import Any
from pydantic import BaseModel, Field
from app.domain.models import WishesState, Message, Change, PendingClarification
from app.docgen.renderer import RenderedDocument


class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: str


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message content")


class ManualCorrectionRequest(BaseModel):
    field: str = Field(..., description="Target field path to update")
    op: str = Field(default="set", description="Operation type: set, add, remove, clear, confirm")
    value: Any = Field(default=None, description="New field value")


class DocumentResponse(BaseModel):
    title: str
    text: str
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)


class SessionDetailResponse(BaseModel):
    session_id: str
    state: WishesState
    messages: list[Message]
    changes: list[Change]
    pending_clarification: PendingClarification | None
    missing_fields: list[str]
    is_complete: bool
    document: DocumentResponse


class MessageTurnResponse(BaseModel):
    session_id: str
    assistant_message: str
    state: WishesState
    changes: list[Change]
    pending_clarification: PendingClarification | None
    missing_fields: list[str]
    is_complete: bool
    document: DocumentResponse
