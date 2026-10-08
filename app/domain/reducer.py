from typing import Any
from app.domain.models import WishesState, Field, FieldStatus, Change, Gift
from app.domain.validators import validate_operation_and_value
from app.domain.rules import apply_conditional_rules


def _get_field_container(state: WishesState, field_path: str) -> Field[Any]:
    if field_path == "executor.name":
        return state.executor.name
    elif field_path == "executor.relationship":
        return state.executor.relationship
    elif hasattr(state, field_path):
        return getattr(state, field_path)
    else:
        raise KeyError(f"Field path '{field_path}' does not exist on WishesState")


def _set_field_container(state: WishesState, field_path: str, new_field: Field[Any]) -> None:
    if field_path == "executor.name":
        state.executor.name = new_field
    elif field_path == "executor.relationship":
        state.executor.relationship = new_field
    elif hasattr(state, field_path):
        setattr(state, field_path, new_field)
    else:
        raise KeyError(f"Field path '{field_path}' does not exist on WishesState")


def apply_operation(
    state: WishesState,
    op: str,
    field: str,
    value: Any = None,
    evidence: str | None = None,
    turn: int = 1,
    is_correction: bool = False,
    status: FieldStatus = FieldStatus.CONFIRMED,
) -> tuple[WishesState, Change | None]:
    """Deterministically applies a single validated operation to WishesState.
    Returns (new_state, change_event).
    """
    validated_value = validate_operation_and_value(field, op, value)

    # Work on a deep copy to ensure immutability of previous state
    new_state = state.model_copy(deep=True)
    current_field = _get_field_container(new_state, field)

    old_value = current_field.value
    old_status = current_field.status

    # Handle No-op if value and status are already identical
    if op == "set" and old_status == status and old_value == validated_value:
        return new_state, None

    change_kind: str = "set"
    updated_value: Any = old_value
    updated_status: FieldStatus = status

    if op == "set":
        updated_value = validated_value
        updated_status = status
        if is_correction or (old_status == FieldStatus.CONFIRMED and old_value is not None and old_value != validated_value):
            change_kind = "correction"
        else:
            change_kind = "set"

    elif op == "add":
        existing_list = list(old_value) if isinstance(old_value, list) else []
        if validated_value not in existing_list:
            existing_list.append(validated_value)
        updated_value = existing_list
        updated_status = FieldStatus.CONFIRMED
        change_kind = "set"

    elif op == "remove":
        existing_list = list(old_value) if isinstance(old_value, list) else []
        # Support removing item by match or item string match for gifts
        if field == "specific_gifts" and isinstance(validated_value, (str, Gift, dict)):
            match_str = validated_value.item if isinstance(validated_value, Gift) else (validated_value.get("item") if isinstance(validated_value, dict) else str(validated_value))
            existing_list = [g for g in existing_list if g.item != match_str]
        else:
            existing_list = [item for item in existing_list if item != validated_value]
        updated_value = existing_list
        updated_status = FieldStatus.CONFIRMED
        change_kind = "clear"

    elif op == "clear":
        updated_value = [] if isinstance(old_value, list) else None
        updated_status = FieldStatus.UNKNOWN
        change_kind = "clear"

    elif op == "confirm":
        updated_status = FieldStatus.CONFIRMED
        change_kind = "confirm"

    # Update field container
    new_field = Field[Any](
        value=updated_value,
        status=updated_status,
        evidence=evidence or current_field.evidence,
        turn=turn,
    )
    _set_field_container(new_state, field, new_field)
    new_state.version += 1

    new_state = apply_conditional_rules(new_state)

    change = Change(
        turn=turn,
        field=field,
        old_value=old_value,
        new_value=updated_value,
        kind=change_kind,
        evidence=evidence,
    )

    return new_state, change



def apply_operations(
    state: WishesState,
    operations: list[dict[str, Any]],
    turn: int = 1,
) -> tuple[WishesState, list[Change]]:
    """Applies a list of operations atomically. If any operation fails, none are applied."""
    current_state = state
    changes: list[Change] = []

    for op_dict in operations:
        current_state, change = apply_operation(
            state=current_state,
            op=op_dict["op"],
            field=op_dict["field"],
            value=op_dict.get("value"),
            evidence=op_dict.get("evidence"),
            turn=turn,
            is_correction=op_dict.get("is_correction", False),
            status=op_dict.get("status", FieldStatus.CONFIRMED),
        )
        if change:
            changes.append(change)

    return current_state, changes


def apply_operations_to_session(
    session: "Session",
    operations: list[dict[str, Any]],
    turn: int = 1,
) -> "Session":
    """Applies operations to a session, records audit changes, and clears resolved pending clarifications."""
    from app.domain.models import Session

    new_session = session.model_copy(deep=True)
    new_state, changes = apply_operations(new_session.state, operations, turn=turn)

    new_session.state = new_state
    new_session.changes.extend(changes)

    # If an explicit correction or update was applied to the field under pending clarification, clear it
    if new_session.pending_clarification:
        clarified_field = new_session.pending_clarification.field
        for c in changes:
            if (
                c.field == clarified_field
                or (clarified_field.startswith("executor") and c.field.startswith("executor"))
                or (clarified_field == "has_children" and c.field in ("has_children", "children"))
                or (clarified_field == "children" and c.field in ("has_children", "children"))
            ):
                new_session.pending_clarification = None
                break

    return new_session

