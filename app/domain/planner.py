from enum import Enum
from typing import Any
from app.domain.models import WishesState, FieldStatus, Session


class PlannerAction(str, Enum):
    RESOLVE_CONTRADICTION = "RESOLVE_CONTRADICTION"
    CONFIRM_UNCONFIRMED = "CONFIRM_UNCONFIRMED"
    ASK_FULL_NAME = "ASK_FULL_NAME"
    ASK_HOME_ADDRESS = "ASK_HOME_ADDRESS"
    ASK_WORLDWIDE_ASSETS = "ASK_WORLDWIDE_ASSETS"
    ASK_HAS_CHILDREN = "ASK_HAS_CHILDREN"
    ASK_CHILDREN_NAMES = "ASK_CHILDREN_NAMES"
    ASK_EXECUTOR_NAME = "ASK_EXECUTOR_NAME"
    ASK_EXECUTOR_RELATIONSHIP = "ASK_EXECUTOR_RELATIONSHIP"
    ASK_SPECIFIC_GIFTS = "ASK_SPECIFIC_GIFTS"
    ASK_ADDITIONAL_WISHES = "ASK_ADDITIONAL_WISHES"
    COMPLETE = "COMPLETE"


def get_missing_fields(state: WishesState) -> list[str]:
    """Returns a list of field identifiers that are still UNKNOWN or UNCONFIRMED."""
    missing: list[str] = []

    if not state.full_name.is_confirmed():
        missing.append("full_name")
    if not state.home_address.is_confirmed():
        missing.append("home_address")
    if not state.covers_worldwide_assets.is_confirmed():
        missing.append("covers_worldwide_assets")
    if not state.has_children.is_confirmed():
        missing.append("has_children")
    elif state.has_children.value is True and not state.children.is_confirmed():
        missing.append("children")
    if not state.executor.name.is_confirmed():
        missing.append("executor.name")
    if not state.executor.relationship.is_confirmed():
        missing.append("executor.relationship")
    if not state.specific_gifts.is_confirmed():
        missing.append("specific_gifts")
    if not state.additional_wishes.is_confirmed():
        missing.append("additional_wishes")

    return missing


def is_state_complete(state: WishesState, has_pending_clarification: bool = False) -> bool:
    """Returns True if every required field is CONFIRMED or NOT_APPLICABLE and no clarification is pending."""
    if has_pending_clarification:
        return False
    return len(get_missing_fields(state)) == 0


def plan_next_action(session: Session) -> tuple[PlannerAction, dict[str, Any]]:
    """Determines the single next workflow action deterministically.
    Strict priority:
    1. Contradiction / Pending Clarification
    2. Unconfirmed provisional values needing user validation
    3. First missing field in standard interview order
    4. COMPLETE
    """
    # 1. Contradiction has highest priority
    if session.pending_clarification:
        return PlannerAction.RESOLVE_CONTRADICTION, {
            "field": session.pending_clarification.field,
            "issue_type": session.pending_clarification.issue_type,
            "question": session.pending_clarification.question_to_ask,
            "conflicting_value": session.pending_clarification.conflicting_value,
        }

    state = session.state

    # 2. Check unconfirmed fields
    unconfirmed_field = _find_first_unconfirmed_field(state)
    if unconfirmed_field:
        field_name, field_obj = unconfirmed_field
        return PlannerAction.CONFIRM_UNCONFIRMED, {
            "field": field_name,
            "value": field_obj.value,
        }

    # 3. Missing fields in order
    if state.full_name.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_FULL_NAME, {}
    if state.home_address.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_HOME_ADDRESS, {}
    if state.covers_worldwide_assets.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_WORLDWIDE_ASSETS, {}
    if state.has_children.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_HAS_CHILDREN, {}
    if state.has_children.is_confirmed() and state.has_children.value is True and state.children.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_CHILDREN_NAMES, {}
    if state.executor.name.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_EXECUTOR_NAME, {}
    if state.executor.relationship.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_EXECUTOR_RELATIONSHIP, {}
    if state.specific_gifts.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_SPECIFIC_GIFTS, {}
    if state.additional_wishes.status == FieldStatus.UNKNOWN:
        return PlannerAction.ASK_ADDITIONAL_WISHES, {}

    # 4. All requirements satisfied
    gifts_val = state.specific_gifts.value or []
    return PlannerAction.COMPLETE, {
        "status": "complete",
        "state_summary": {
            "full_name": state.full_name.value,
            "home_address": state.home_address.value,
            "covers_worldwide_assets": state.covers_worldwide_assets.value,
            "has_children": state.has_children.value,
            "children": state.children.value,
            "executor_name": state.executor.name.value,
            "executor_relationship": state.executor.relationship.value,
            "specific_gifts": [g.model_dump() if hasattr(g, "model_dump") else g for g in gifts_val],
            "additional_wishes": state.additional_wishes.value,
        }
    }


def _find_first_unconfirmed_field(state: WishesState) -> tuple[str, Any] | None:
    for name in [
        "full_name",
        "home_address",
        "covers_worldwide_assets",
        "has_children",
        "children",
        "specific_gifts",
        "additional_wishes",
    ]:
        f = getattr(state, name)
        if f.status == FieldStatus.UNCONFIRMED:
            return name, f

    if state.executor.name.status == FieldStatus.UNCONFIRMED:
        return "executor.name", state.executor.name
    if state.executor.relationship.status == FieldStatus.UNCONFIRMED:
        return "executor.relationship", state.executor.relationship

    return None
