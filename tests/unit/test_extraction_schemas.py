import pytest
from pydantic import ValidationError
from app.llm.schemas import (
    ExtractionResult,
    ExtractionOperation,
    ExtractionAmbiguity,
    ExtractionContradiction,
)


def test_valid_extraction_result_parsing():
    raw_dict = {
        "user_intent": "provide_info",
        "operations": [
            {
                "op": "set",
                "field": "full_name",
                "value": "Jane Smith",
                "evidence": "My name is Jane Smith",
                "confidence": "high",
                "is_correction": False,
            }
        ],
        "ambiguities": [],
        "contradictions": [],
    }

    result = ExtractionResult.model_validate(raw_dict)
    assert result.user_intent == "provide_info"
    assert len(result.operations) == 1
    assert result.operations[0].op == "set"
    assert result.operations[0].field == "full_name"
    assert result.operations[0].value == "Jane Smith"
    assert result.operations[0].evidence == "My name is Jane Smith"
    assert result.operations[0].confidence == "high"
    assert result.operations[0].is_correction is False


def test_extraction_with_ambiguities_and_contradictions():
    raw_dict = {
        "user_intent": "unclear",
        "operations": [],
        "ambiguities": [
            {
                "field": "children",
                "evidence": "a few kids",
                "issue": "Specific names not provided",
            }
        ],
        "contradictions": [
            {
                "field": "has_children",
                "evidence": "my son",
                "conflicting_value": "son",
                "explanation": "Previously stated no children",
            }
        ],
    }

    result = ExtractionResult.model_validate(raw_dict)
    assert len(result.ambiguities) == 1
    assert result.ambiguities[0].field == "children"
    assert len(result.contradictions) == 1
    assert result.contradictions[0].conflicting_value == "son"


def test_invalid_operation_type_rejected():
    raw_dict = {
        "user_intent": "provide_info",
        "operations": [
            {
                "op": "invalid_op",  # Not in ("set", "add", "remove", "clear", "confirm")
                "field": "full_name",
                "value": "Jane",
                "evidence": "Jane",
            }
        ],
    }
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(raw_dict)


def test_missing_evidence_rejected():
    raw_dict = {
        "user_intent": "provide_info",
        "operations": [
            {
                "op": "set",
                "field": "full_name",
                "value": "Jane",
                # missing 'evidence'
            }
        ],
    }
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(raw_dict)
