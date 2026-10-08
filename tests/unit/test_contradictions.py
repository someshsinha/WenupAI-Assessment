from app.domain.models import WishesState, Field, FieldStatus, Session, PendingClarification
from app.domain.contradictions import detect_contradictions
from app.domain.reducer import apply_operation, apply_operations_to_session


def test_unacknowledged_contradiction_detected_and_not_overwritten():
    state = WishesState(
        full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED)
    )

    # Proposed operation without correction semantics
    proposed_ops = [
        {"op": "set", "field": "full_name", "value": "Alice Johnson", "is_correction": False}
    ]

    contradictions = detect_contradictions(state, proposed_ops, user_message="Alice Johnson")
    assert len(contradictions) == 1
    assert contradictions[0].field == "full_name"
    assert contradictions[0].issue_type == "contradiction"

    # Confirmed state must remain unchanged
    assert state.full_name.value == "Alice Smith"


def test_children_contradiction_when_has_children_confirmed_false():
    state = WishesState(
        has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
        children=Field[list[str]](status=FieldStatus.NOT_APPLICABLE),
    )

    user_msg = "Leave my car to my son Aarav"
    proposed_ops = [
        {"op": "add", "field": "specific_gifts", "value": {"item": "car", "recipient": "son Aarav"}}
    ]

    contradictions = detect_contradictions(state, proposed_ops, user_message=user_msg)
    assert len(contradictions) == 1
    assert contradictions[0].field == "has_children"
    assert "Earlier you stated that you do not have children" in contradictions[0].question_to_ask

    # State remains confirmed False
    assert state.has_children.value is False


def test_children_contradiction_when_has_children_confirmed_true_and_user_says_no_children():
    state = WishesState(
        has_children=Field[bool](value=True, status=FieldStatus.CONFIRMED),
        children=Field[list[str]](value=["Aarav", "Anaya"], status=FieldStatus.CONFIRMED),
    )

    user_msg = "Actually, I don't have any children."
    proposed_ops = [
        {"op": "set", "field": "has_children", "value": False, "evidence": "I don't have any children", "is_correction": False}
    ]

    contradictions = detect_contradictions(state, proposed_ops, user_message=user_msg)
    assert len(contradictions) == 1
    assert contradictions[0].field == "has_children"
    assert contradictions[0].issue_type == "contradiction"
    assert "Earlier you stated that you have children" in contradictions[0].question_to_ask

    # State remains confirmed True
    assert state.has_children.value is True
    assert state.children.value == ["Aarav", "Anaya"]



def test_explicit_correction_is_not_treated_as_contradiction():
    state = WishesState(
        full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED)
    )

    # User explicitly corrects
    proposed_ops = [
        {"op": "set", "field": "full_name", "value": "Alice Johnson", "is_correction": True}
    ]

    contradictions = detect_contradictions(state, proposed_ops, user_message="Actually, my name is Alice Johnson")
    assert len(contradictions) == 0


def test_resolving_contradiction_with_explicit_correction():
    session = Session(
        id="test_sess_conflict",
        state=WishesState(
            has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
        ),
        pending_clarification=PendingClarification(
            field="has_children",
            issue_type="contradiction",
            user_statement="my son Aarav",
            conflicting_value="son Aarav",
        ),
    )

    # User clarifies: "Actually I do have a son named Aarav"
    updated_session = apply_operations_to_session(
        session=session,
        operations=[
            {"op": "set", "field": "has_children", "value": True, "is_correction": True},
            {"op": "add", "field": "children", "value": "Aarav", "is_correction": False},
        ],
        turn=2,
    )

    assert updated_session.state.has_children.value is True
    assert updated_session.state.children.value == ["Aarav"]
    assert updated_session.pending_clarification is None
