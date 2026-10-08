from datetime import datetime, timezone
from app.domain.models import (
    Field,
    FieldStatus,
    Executor,
    Gift,
    WishesState,
    Change,
    PendingClarification,
    Message,
    Session,
)


def test_field_initial_state():
    field = Field[str]()
    assert field.value is None
    assert field.status == FieldStatus.UNKNOWN
    assert field.evidence is None
    assert field.turn is None
    assert not field.is_confirmed()
    assert not field.is_known_or_applicable()


def test_field_confirmed_and_applicable():
    field = Field[str](
        value="Jane Doe",
        status=FieldStatus.CONFIRMED,
        evidence="My name is Jane Doe",
        turn=1,
    )
    assert field.value == "Jane Doe"
    assert field.is_confirmed()
    assert field.is_known_or_applicable()

    na_field = Field[list[str]](status=FieldStatus.NOT_APPLICABLE)
    assert not na_field.is_confirmed()
    assert na_field.is_known_or_applicable()


def test_wishes_state_defaults():
    state = WishesState()
    assert state.full_name.status == FieldStatus.UNKNOWN
    assert state.home_address.status == FieldStatus.UNKNOWN
    assert state.covers_worldwide_assets.status == FieldStatus.UNKNOWN
    assert state.has_children.status == FieldStatus.UNKNOWN
    assert state.children.status == FieldStatus.UNKNOWN
    assert state.executor.name.status == FieldStatus.UNKNOWN
    assert state.executor.relationship.status == FieldStatus.UNKNOWN
    assert state.specific_gifts.status == FieldStatus.UNKNOWN
    assert state.additional_wishes.status == FieldStatus.UNKNOWN
    assert state.version == 0


def test_wishes_state_with_nested_objects():
    state = WishesState(
        full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
        executor=Executor(
            name=Field[str](value="Bob Smith", status=FieldStatus.CONFIRMED),
            relationship=Field[str](value="brother", status=FieldStatus.CONFIRMED),
        ),
        specific_gifts=Field[list[Gift]](
            value=[Gift(item="Gold Watch", recipient="Bob")],
            status=FieldStatus.CONFIRMED,
        ),
        additional_wishes=Field[list[str]](
            value=["Scatter ashes in the sea"],
            status=FieldStatus.CONFIRMED,
        ),
    )
    assert state.full_name.value == "Alice Smith"
    assert state.executor.name.value == "Bob Smith"
    assert state.executor.relationship.value == "brother"
    assert len(state.specific_gifts.value) == 1
    assert state.specific_gifts.value[0].item == "Gold Watch"
    assert state.specific_gifts.value[0].recipient == "Bob"
    assert state.additional_wishes.value == ["Scatter ashes in the sea"]


def test_change_model():
    change = Change(
        turn=1,
        field="full_name",
        old_value=None,
        new_value="Alice Smith",
        kind="set",
        evidence="I am Alice Smith",
    )
    assert change.field == "full_name"
    assert change.kind == "set"
    assert change.new_value == "Alice Smith"
    assert isinstance(change.timestamp, datetime)


def test_pending_clarification_model():
    clarification = PendingClarification(
        field="has_children",
        issue_type="contradiction",
        user_statement="leave it to my son",
        conflicting_value="son mentioned when previously answered no children",
        question_to_ask="Earlier you mentioned having no children, but now you mentioned a son. Could you clarify?",
    )
    assert clarification.field == "has_children"
    assert clarification.issue_type == "contradiction"


def test_session_model():
    session = Session(id="sess_123")
    assert session.id == "sess_123"
    assert session.state.version == 0
    assert len(session.messages) == 0
    assert len(session.changes) == 0
    assert session.pending_clarification is None

    session.messages.append(
        Message(role="user", content="Hello", turn=1)
    )
    assert len(session.messages) == 1
    assert session.messages[0].content == "Hello"
