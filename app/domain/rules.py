from app.domain.models import WishesState, FieldStatus


def apply_conditional_rules(state: WishesState) -> WishesState:
    """Applies conditional cascading rules to the structured state.
    Ensures dependent fields are marked NOT_APPLICABLE or UNKNOWN appropriately.
    """
    updated_state = state.model_copy(deep=True)

    # Rule 1: has_children == False -> children is NOT_APPLICABLE
    if updated_state.has_children.is_confirmed() and updated_state.has_children.value is False:
        updated_state.children.status = FieldStatus.NOT_APPLICABLE
        updated_state.children.value = None

    # Rule 2: has_children == True -> children must be UNKNOWN or CONFIRMED list (never NOT_APPLICABLE)
    elif updated_state.has_children.is_confirmed() and updated_state.has_children.value is True:
        if updated_state.children.status == FieldStatus.NOT_APPLICABLE:
            updated_state.children.status = FieldStatus.UNKNOWN
            updated_state.children.value = None

    return updated_state
