import pytest
from app.domain.models import WishesState, FieldStatus, Gift
from app.domain.reducer import apply_operation, apply_operations
from app.domain.validators import ValidationError


def test_reducer_set_scalar_field():
    initial_state = WishesState()
    new_state, change = apply_operation(
        state=initial_state,
        op="set",
        field="full_name",
        value="Jane Doe",
        evidence="My name is Jane Doe",
        turn=1,
    )

    assert new_state.full_name.value == "Jane Doe"
    assert new_state.full_name.status == FieldStatus.CONFIRMED
    assert new_state.full_name.evidence == "My name is Jane Doe"
    assert new_state.full_name.turn == 1
    assert new_state.version == 1

    # Ensure original state was not mutated
    assert initial_state.full_name.value is None
    assert initial_state.version == 0

    assert change is not None
    assert change.field == "full_name"
    assert change.old_value is None
    assert change.new_value == "Jane Doe"
    assert change.kind == "set"


def test_reducer_nested_executor_field():
    initial_state = WishesState()
    state_step1, change1 = apply_operation(
        state=initial_state,
        op="set",
        field="executor.name",
        value="James Smith",
        evidence="my brother James Smith",
        turn=1,
    )
    state_step2, change2 = apply_operation(
        state=state_step1,
        op="set",
        field="executor.relationship",
        value="brother",
        evidence="my brother",
        turn=1,
    )

    assert state_step2.executor.name.value == "James Smith"
    assert state_step2.executor.relationship.value == "brother"
    assert state_step2.executor.name.status == FieldStatus.CONFIRMED
    assert state_step2.executor.relationship.status == FieldStatus.CONFIRMED
    assert state_step2.version == 2


def test_reducer_list_operations():
    state = WishesState()

    # Add first child
    state, c1 = apply_operation(state, "add", "children", value="Alice", turn=1)
    assert state.children.value == ["Alice"]
    assert state.children.status == FieldStatus.CONFIRMED

    # Add second child
    state, c2 = apply_operation(state, "add", "children", value="Bob", turn=2)
    assert state.children.value == ["Alice", "Bob"]

    # Remove child
    state, c3 = apply_operation(state, "remove", "children", value="Alice", turn=3)
    assert state.children.value == ["Bob"]
    assert c3.kind == "clear"


def test_reducer_specific_gifts_operations():
    state = WishesState()
    gift_dict = {"item": "Vintage Guitar", "recipient": "Sarah"}

    state, change = apply_operation(
        state=state,
        op="add",
        field="specific_gifts",
        value=gift_dict,
        turn=1,
    )
    assert len(state.specific_gifts.value) == 1
    assert state.specific_gifts.value[0].item == "Vintage Guitar"
    assert state.specific_gifts.value[0].recipient == "Sarah"

    # Remove gift
    state, change = apply_operation(
        state=state,
        op="remove",
        field="specific_gifts",
        value="Vintage Guitar",
        turn=2,
    )
    assert len(state.specific_gifts.value) == 0


def test_reducer_rejects_unknown_field():
    state = WishesState()
    with pytest.raises(ValidationError, match="Unknown field path: 'favorite_color'"):
        apply_operation(state, "set", "favorite_color", "Blue")


def test_reducer_rejects_invalid_operation():
    state = WishesState()
    with pytest.raises(ValidationError, match="Operation 'add' is not allowed for field 'full_name'"):
        apply_operation(state, "add", "full_name", "Jane")


def test_reducer_rejects_invalid_types():
    state = WishesState()

    # Empty string
    with pytest.raises(ValidationError, match="expects a non-empty string"):
        apply_operation(state, "set", "full_name", "   ")

    # Invalid boolean
    with pytest.raises(ValidationError, match="expects a boolean"):
        apply_operation(state, "set", "covers_worldwide_assets", "yes_please")


def test_reducer_idempotent_no_change():
    state = WishesState()
    state, change1 = apply_operation(state, "set", "full_name", "Jane Doe", turn=1)
    assert change1 is not None

    # Apply same value again
    state2, change2 = apply_operation(state, "set", "full_name", "Jane Doe", turn=2)
    assert change2 is None
    assert state2.version == state.version


def test_batch_apply_operations_atomic():
    state = WishesState()
    ops = [
        {"op": "set", "field": "full_name", "value": "Jane Smith", "evidence": "I am Jane"},
        {"op": "set", "field": "has_children", "value": False, "evidence": "no children"},
        {"op": "set", "field": "covers_worldwide_assets", "value": True, "evidence": "worldwide"},
    ]
    new_state, changes = apply_operations(state, ops, turn=1)

    assert new_state.full_name.value == "Jane Smith"
    assert new_state.has_children.value is False
    assert new_state.covers_worldwide_assets.value is True
    assert len(changes) == 3
    assert new_state.version == 3
