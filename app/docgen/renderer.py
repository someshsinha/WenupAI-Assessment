from pydantic import BaseModel, Field
from app.domain.models import WishesState, FieldStatus
from app.domain.planner import get_missing_fields, is_state_complete


class RenderedDocument(BaseModel):
    """Structured representation of the rendered draft document."""
    title: str = "Personal Wishes Document"
    text: str
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)


def render_wishes_document(
    state: WishesState,
    has_pending_clarification: bool = False,
) -> RenderedDocument:
    """Deterministically renders a formatted Personal Wishes Document strictly from confirmed state.
    No LLM calls or conversation history are involved.
    """
    missing = get_missing_fields(state)
    complete = is_state_complete(state, has_pending_clarification)

    lines = [
        "==================================================================",
        "             FICTIONAL PERSONAL WISHES DRAFT",
        "                     NOT LEGAL ADVICE",
        "==================================================================",
        "IMPORTANT NOTICE:",
        "This document is a FICTIONAL DRAFT generated solely for demonstration",
        "and technical evaluation purposes. It DOES NOT constitute legal advice,",
        "a valid will, or a legally binding instrument under any jurisdiction.",
        "==================================================================",
        "",
        "PERSONAL WISHES DECLARATION",
        "------------------------------------------------------------------",
    ]

    # 1. Principal Information
    name_str = state.full_name.value if state.full_name.is_confirmed() else "[Not yet provided]"
    address_str = state.home_address.value if state.home_address.is_confirmed() else "[Not yet provided]"

    lines.extend([
        "1. PRINCIPAL IDENTIFICATION",
        f"   Full Legal Name: {name_str}",
        f"   Residential Address: {address_str}",
        "",
    ])

    # 2. Scope of Assets
    if state.covers_worldwide_assets.is_confirmed():
        if state.covers_worldwide_assets.value:
            scope_str = "This declaration applies to all my assets and personal effects WORLDWIDE."
        else:
            scope_str = "This declaration applies to my assets located in my PRIMARY RESIDENTIAL JURISDICTION only."
    else:
        scope_str = "[Asset territorial scope not yet specified]"

    lines.extend([
        "2. JURISDICTION & ASSET COVERAGE",
        f"   {scope_str}",
        "",
    ])

    # 3. Children
    lines.append("3. FAMILY & CHILDREN")
    if state.has_children.is_confirmed():
        if state.has_children.value is False:
            lines.append("   I declare that I have no children.")
        else:
            if state.children.is_confirmed() and state.children.value:
                lines.append("   I declare that I have the following child(ren):")
                for child in state.children.value:
                    lines.append(f"   - {child}")
            else:
                lines.append("   I have children: [Names not yet provided]")
    else:
        lines.append("   [Family status not yet provided]")
    lines.append("")

    # 4. Executor
    lines.append("4. APPOINTMENT OF EXECUTOR")
    exec_name = state.executor.name.value if state.executor.name.is_confirmed() else None
    exec_rel = state.executor.relationship.value if state.executor.relationship.is_confirmed() else None

    if exec_name and exec_rel:
        lines.append(f"   I appoint my {exec_rel}, {exec_name}, as the executor of these personal wishes.")
    elif exec_name:
        lines.append(f"   I appoint {exec_name} as the executor of these personal wishes.")
    elif exec_rel:
        lines.append(f"   I appoint my {exec_rel} [Name not yet provided] as the executor of these personal wishes.")
    else:
        lines.append("   [Executor not yet appointed]")
    lines.append("")

    # 5. Specific Gifts
    lines.append("5. SPECIFIC GIFTS & BEQUESTS")
    if state.specific_gifts.is_confirmed():
        if state.specific_gifts.value and len(state.specific_gifts.value) > 0:
            for gift in state.specific_gifts.value:
                recip_str = f" to {gift.recipient}" if gift.recipient else ""
                lines.append(f"   - Gift: {gift.item}{recip_str}")
        else:
            lines.append("   None specified.")
    else:
        lines.append("   [Specific gifts not yet specified]")
    lines.append("")

    # 6. Additional Wishes
    lines.append("6. ADDITIONAL WISHES & SPECIAL INSTRUCTIONS")
    if state.additional_wishes.is_confirmed():
        if state.additional_wishes.value and len(state.additional_wishes.value) > 0:
            for wish in state.additional_wishes.value:
                lines.append(f"   - {wish}")
        else:
            lines.append("   None specified.")
    else:
        lines.append("   [Additional wishes not yet specified]")
    lines.append("")

    lines.extend([
        "------------------------------------------------------------------",
        f"Document Status: {'COMPLETE' if complete else 'IN PROGRESS (DRAFT)'}",
        "==================================================================",
    ])

    full_text = "\n".join(lines)

    return RenderedDocument(
        title="Personal Wishes Document",
        text=full_text,
        is_complete=complete,
        missing_fields=missing,
    )
