from enum import Enum
from typing import Generic, TypeVar, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field as PyField

T = TypeVar("T")


class FieldStatus(str, Enum):
    UNKNOWN = "unknown"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    NOT_APPLICABLE = "not_applicable"


class Field(BaseModel, Generic[T]):
    """Represents a structured state field with value, status, and audit evidence."""
    value: T | None = None
    status: FieldStatus = FieldStatus.UNKNOWN
    evidence: str | None = None
    turn: int | None = None

    def is_confirmed(self) -> bool:
        return self.status == FieldStatus.CONFIRMED

    def is_known_or_applicable(self) -> bool:
        return self.status in (FieldStatus.CONFIRMED, FieldStatus.NOT_APPLICABLE)


class Executor(BaseModel):
    name: Field[str] = PyField(default_factory=Field)
    relationship: Field[str] = PyField(default_factory=Field)


class Gift(BaseModel):
    item: str
    recipient: str | None = None


class WishesState(BaseModel):
    full_name: Field[str] = PyField(default_factory=Field)
    home_address: Field[str] = PyField(default_factory=Field)
    covers_worldwide_assets: Field[bool] = PyField(default_factory=Field)
    has_children: Field[bool] = PyField(default_factory=Field)
    children: Field[list[str]] = PyField(default_factory=Field)
    executor: Executor = PyField(default_factory=Executor)
    specific_gifts: Field[list[Gift]] = PyField(default_factory=Field)
    additional_wishes: Field[list[str]] = PyField(default_factory=Field)
    version: int = 0


class Change(BaseModel):
    turn: int
    field: str
    old_value: Any = None
    new_value: Any = None
    kind: Literal["set", "correction", "clear", "confirm"]
    evidence: str | None = None
    timestamp: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))


class PendingClarification(BaseModel):
    field: str
    issue_type: Literal["contradiction", "ambiguity", "unconfirmed"]
    user_statement: str
    conflicting_value: Any = None
    question_to_ask: str | None = None


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    turn: int
    timestamp: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))


class Session(BaseModel):
    id: str
    state: WishesState = PyField(default_factory=WishesState)
    messages: list[Message] = PyField(default_factory=list)
    changes: list[Change] = PyField(default_factory=list)
    pending_clarification: PendingClarification | None = None
    created_at: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = PyField(default_factory=lambda: datetime.now(timezone.utc))
