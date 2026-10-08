from typing import Any
import re
from app.domain.models import WishesState, FieldStatus, PendingClarification


def detect_contradictions(
    state: WishesState,
    operations: list[dict[str, Any]],
    user_message: str = "",
) -> list[PendingClarification]:
    """Detects contradictions between proposed operations/user statements and already confirmed state.
    Returns a list of PendingClarification objects.
    """
    contradictions: list[PendingClarification] = []

    # 1. Check operations that try to overwrite a confirmed field without is_correction=True
    for op_dict in operations:
        field = op_dict.get("field")
        new_val = op_dict.get("value")
        is_corr = op_dict.get("is_correction", False)
        op = op_dict.get("op", "set")

        if not field or is_corr:
            continue

        current_val, is_confirmed = _get_field_status_and_val(state, field)

        if is_confirmed and current_val is not None:
            # If changing confirmed scalar value to a different value without explicit correction
            if op == "set" and current_val != new_val:
                contradictions.append(
                    PendingClarification(
                        field=field,
                        issue_type="contradiction",
                        user_statement=user_message or str(new_val),
                        conflicting_value=new_val,
                        question_to_ask=(
                            f"Earlier you mentioned {field.replace('.', ' ')} was '{current_val}', "
                            f"but now you mentioned '{new_val}'. Could you clarify which one is correct?"
                        ),
                    )
                )

    # 2. Semantic Cross-field contradiction checks:
    # E.g. has_children is confirmed False, but user mentions 'son', 'daughter', 'kids', 'children', or adds a child/gift to child
    if state.has_children.is_confirmed() and state.has_children.value is False:
        # Check operations targeting children
        for op_dict in operations:
            if op_dict.get("field") == "children" and not op_dict.get("is_correction"):
                contradictions.append(
                    PendingClarification(
                        field="has_children",
                        issue_type="contradiction",
                        user_statement=user_message,
                        conflicting_value=op_dict.get("value"),
                        question_to_ask=(
                            "Earlier you stated that you do not have children, but you just mentioned children. "
                            "Could you clarify if you would like to include your children?"
                        ),
                    )
                )

        # Check user message text for references to child/son/daughter
        child_keywords = re.compile(r"\b(my son|my daughter|my child|my children|my kids)\b", re.IGNORECASE)
        if user_message and child_keywords.search(user_message) and not any(c.field == "has_children" for c in contradictions):
            # Only trigger if not an explicit correction
            if not any(op_dict.get("field") == "has_children" and op_dict.get("is_correction") for op_dict in operations):
                contradictions.append(
                    PendingClarification(
                        field="has_children",
                        issue_type="contradiction",
                        user_statement=user_message,
                        conflicting_value=user_message,
                        question_to_ask=(
                            "Earlier you stated that you do not have children, but your message mentioned a child or son/daughter. "
                            "Could you clarify if you have children you'd like to include?"
                        ),
                    )
                )

    return contradictions


def _get_field_status_and_val(state: WishesState, field: str) -> tuple[Any, bool]:
    if field == "executor.name":
        return state.executor.name.value, state.executor.name.is_confirmed()
    elif field == "executor.relationship":
        return state.executor.relationship.value, state.executor.relationship.is_confirmed()
    elif hasattr(state, field):
        f = getattr(state, field)
        return f.value, f.is_confirmed()
    return None, False
