from app.domain.models import WishesState, FieldStatus
from app.domain.reducer import apply_operation, apply_operations


def test_no_children_cascades_children_to_not_applicable():
    state = WishesState()
    assert state.children.status == FieldStatus.UNKNOWN

    # User says "I have no children"
    state, change = apply_operation(state, "set", "has_children", value=False, turn=1)
    assert state.has_children.value is False
    assert state.has_children.status == FieldStatus.CONFIRMED
    assert state.children.status == FieldStatus.NOT_APPLICABLE
    assert state.children.value is None


def test_changing_no_children_to_has_children_resets_children_to_unknown():
    state = WishesState()
    state, _ = apply_operation(state, "set", "has_children", value=False, turn=1)
    assert state.children.status == FieldStatus.NOT_APPLICABLE

    # User corrects: "Actually I do have children"
    state, _ = apply_operation(state, "set", "has_children", value=True, turn=2, is_correction=True)
    assert state.has_children.value is True
    assert state.children.status == FieldStatus.UNKNOWN


def test_explicit_no_gifts_is_confirmed_empty_list():
    state = WishesState()
    assert state.specific_gifts.status == FieldStatus.UNKNOWN
    assert state.specific_gifts.value is None

    # User says: "I don't have any specific gifts"
    state, change = apply_operation(state, "set", "specific_gifts", value=[], turn=1)
    assert state.specific_gifts.status == FieldStatus.CONFIRMED
    assert state.specific_gifts.value == []
    # This is confirmed empty, distinct from UNKNOWN


def test_explicit_no_additional_wishes_is_confirmed_empty_list():
    state = WishesState()
    assert state.additional_wishes.status == FieldStatus.UNKNOWN

    # User says: "No additional wishes"
    state, change = apply_operation(state, "set", "additional_wishes", value=[], turn=1)
    assert state.additional_wishes.status == FieldStatus.CONFIRMED
    assert state.additional_wishes.value == []


def test_executor_relationship_without_name_leaves_name_unknown():
    state = WishesState()
    state, change = apply_operation(state, "set", "executor.relationship", value="brother", turn=1)

    assert state.executor.relationship.value == "brother"
    assert state.executor.relationship.status == FieldStatus.CONFIRMED
    assert state.executor.name.value is None
    assert state.executor.name.status == FieldStatus.UNKNOWN
