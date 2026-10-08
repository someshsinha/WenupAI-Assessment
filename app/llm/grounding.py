import re
from typing import Sequence
from app.llm.schemas import ExtractionOperation


def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing, collapsing whitespace, and stripping outer punctuation."""
    if not text:
        return ""
    # Lowercase
    t = text.lower()
    # Replace non-alphanumeric chars with spaces except single internal quotes
    t = re.sub(r"[^\w\s]", " ", t)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_evidence_grounded(evidence: str, user_message: str, threshold: float = 0.7) -> bool:
    """Validates whether the extracted evidence is grounded in the current user message.
    Uses normalized substring containment and token-overlap ratio.
    """
    if not evidence or not user_message:
        return False

    norm_evidence = normalize_text(evidence)
    norm_user = normalize_text(user_message)

    if not norm_evidence or not norm_user:
        return False

    # 1. Exact normalized substring match
    if norm_evidence in norm_user:
        return True

    # 2. Token overlap check for slight rephrasing / omitted filler words
    ev_tokens = set(norm_evidence.split())
    user_tokens = set(norm_user.split())

    if not ev_tokens:
        return False

    # Compute what proportion of evidence words exist in user message
    matching_tokens = ev_tokens.intersection(user_tokens)
    overlap_ratio = len(matching_tokens) / len(ev_tokens)

    return overlap_ratio >= threshold


def filter_grounded_operations(
    operations: Sequence[ExtractionOperation],
    user_message: str,
) -> tuple[list[ExtractionOperation], list[ExtractionOperation]]:
    """Separates operations into grounded and ungrounded/quarantined lists."""
    grounded: list[ExtractionOperation] = []
    ungrounded: list[ExtractionOperation] = []

    for op in operations:
        if is_evidence_grounded(op.evidence, user_message):
            grounded.append(op)
        else:
            ungrounded.append(op)

    return grounded, ungrounded
