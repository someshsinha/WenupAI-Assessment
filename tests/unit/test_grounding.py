from app.llm.schemas import ExtractionOperation
from app.llm.grounding import (
    normalize_text,
    is_evidence_grounded,
    filter_grounded_operations,
)


def test_normalization():
    raw = "  Hello,   World! -- This is a TEST. "
    assert normalize_text(raw) == "hello world this is a test"


def test_evidence_grounded_exact_and_case_insensitive():
    user_msg = "My name is Jane Smith and I live in London."
    assert is_evidence_grounded("Jane Smith", user_msg)
    assert is_evidence_grounded("jane smith", user_msg)
    assert is_evidence_grounded("Jane Smith.", user_msg)
    assert is_evidence_grounded("  JANE   SMITH  ", user_msg)


def test_evidence_grounded_token_overlap():
    user_msg = "I appoint my dear brother James Smith as executor"
    # Evidence slightly rephrased / trimmed
    evidence = "brother James Smith"
    assert is_evidence_grounded(evidence, user_msg)


def test_evidence_fabricated_rejected():
    user_msg = "I live in Paris."
    fabricated_evidence = "I have three children named Maya, Leo, and Noah"
    assert not is_evidence_grounded(fabricated_evidence, user_msg)


def test_evidence_from_previous_message_rejected():
    # User message in turn 2 does not contain full name
    turn_2_user_msg = "Yes, covers worldwide assets."
    turn_1_evidence = "Jane Smith"
    assert not is_evidence_grounded(turn_1_evidence, turn_2_user_msg)


def test_filter_grounded_operations():
    user_msg = "My name is Alice and I have no children."

    ops = [
        ExtractionOperation(
            op="set",
            field="full_name",
            value="Alice",
            evidence="My name is Alice",
        ),
        ExtractionOperation(
            op="set",
            field="has_children",
            value=False,
            evidence="have no children",
        ),
        ExtractionOperation(
            op="set",
            field="home_address",
            value="10 Downing St",
            evidence="10 Downing St London",  # Hallucinated / not in user_msg
        ),
    ]

    grounded, ungrounded = filter_grounded_operations(ops, user_msg)
    assert len(grounded) == 2
    assert len(ungrounded) == 1
    assert ungrounded[0].field == "home_address"
