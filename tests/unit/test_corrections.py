from app.domain.models import WishesState, Field, FieldStatus, Session, PendingClarification
from app.domain.reducer import apply_operation, apply_operations_to_session


def test_explicit_correction_replaces_confirmed_scalar():
    # Initial state with Jane Doe
    state = WishesState(
        full_name=Field[str](
            value="Jane Doe",
            status=FieldStatus.CONFIRMED,
            evidence="I am Jane Doe",
            turn=1,
        )
    )

    # User says: "Actually, my name is Jane Smith"
    new_state, change = apply_operation(
        state=state,
        op="set",
        field="full_name",
        value="Jane Smith",
        evidence="Actually, my name is Jane Smith",
        turn=2,
        is_correction=True,
    )

    assert new_state.full_name.value == "Jane Smith"
    assert new_state.full_name.status == FieldStatus.CONFIRMED
    assert change is not None
    assert change.kind == "correction"
    assert change.old_value == "Jane Doe"
    assert change.new_value == "Jane Smith"
    assert change.turn == 2


def test_explicit_correction_replaces_executor_name():
    state = WishesState()
    state, _ = apply_operation(state, "set", "executor.name", "James", turn=1)
    state, _ = apply_operation(state, "set", "executor.relationship", "brother", turn=1)

    assert state.executor.name.value == "James"

    # User correction: "Actually, Bob is my executor, not James."
    state, change = apply_operation(
        state=state,
        op="set",
        field="executor.name",
        value="Bob",
        evidence="Actually, Bob is my executor, not James.",
        turn=2,
        is_correction=True,
    )

    assert state.executor.name.value == "Bob"
    assert state.executor.relationship.value == "brother"  # unchanged
    assert change.kind == "correction"
    assert change.old_value == "James"
    assert change.new_value == "Bob"


def test_explicit_correction_clears_pending_clarification_on_session():
    session = Session(
        id="test_sess_1",
        state=WishesState(
            executor=WishesState().executor
        ),
        pending_clarification=PendingClarification(
            field="executor.name",
            issue_type="ambiguity",
            user_statement="my brother",
            question_to_ask="What is your brother's name?",
        ),
    )

    # User provides: "My brother's name is Robert"
    updated_session = apply_operations_to_session(
        session=session,
        operations=[
            {
                "op": "set",
                "field": "executor.name",
                "value": "Robert",
                "evidence": "My brother's name is Robert",
                "is_correction": False,
            }
        ],
        turn=2,
    )

    assert updated_session.state.executor.name.value == "Robert"
    assert updated_session.pending_clarification is None
    assert len(updated_session.changes) == 1
