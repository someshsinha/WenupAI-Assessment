from typing import Any, Literal
from pydantic import BaseModel, Field


OperationType = Literal["set", "add", "remove", "clear", "confirm"]
ConfidenceLevel = Literal["high", "medium", "low"]
UserIntent = Literal[
    "provide_info",
    "correction",
    "confirmation",
    "denial",
    "question",
    "off_topic",
    "unclear",
]


class ExtractionOperation(BaseModel):
    """An atomic state mutation proposed by the LLM from user input."""
    op: OperationType
    field: str
    value: Any = None
    evidence: str
    confidence: ConfidenceLevel = "high"
    is_correction: bool = False


class ExtractionAmbiguity(BaseModel):
    """Ambiguous or vague statement detected during extraction."""
    field: str | None = None
    evidence: str | None = None
    issue: str


class ExtractionContradiction(BaseModel):
    """Contradiction or conflict identified during extraction."""
    field: str
    evidence: str
    conflicting_value: Any = None
    explanation: str | None = None


class ExtractionResult(BaseModel):
    """Strict structured object returned by the LLM extractor."""
    user_intent: UserIntent = "provide_info"
    operations: list[ExtractionOperation] = Field(default_factory=list)
    ambiguities: list[ExtractionAmbiguity] = Field(default_factory=list)
    contradictions: list[ExtractionContradiction] = Field(default_factory=list)
