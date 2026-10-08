from app.domain.models import WishesState, Field, FieldStatus, Executor, Gift
from app.docgen.renderer import render_wishes_document


def test_renderer_mandatory_disclaimer_present():
    state = WishesState()
    doc = render_wishes_document(state)

    assert "FICTIONAL PERSONAL WISHES DRAFT" in doc.text
    assert "NOT LEGAL ADVICE" in doc.text
    assert "DOES NOT constitute legal advice" in doc.text
    assert not doc.is_complete
    assert len(doc.missing_fields) > 0


def test_renderer_complete_state_with_children_and_gifts():
    state = WishesState(
        full_name=Field[str](value="Jane Doe", status=FieldStatus.CONFIRMED),
        home_address=Field[str](value="10 Downing Street, London", status=FieldStatus.CONFIRMED),
        covers_worldwide_assets=Field[bool](value=True, status=FieldStatus.CONFIRMED),
        has_children=Field[bool](value=True, status=FieldStatus.CONFIRMED),
        children=Field[list[str]](value=["Alice", "Bob"], status=FieldStatus.CONFIRMED),
        executor=Executor(
            name=Field[str](value="James Doe", status=FieldStatus.CONFIRMED),
            relationship=Field[str](value="brother", status=FieldStatus.CONFIRMED),
        ),
        specific_gifts=Field[list[Gift]](
            value=[Gift(item="Gold Watch", recipient="Alice")],
            status=FieldStatus.CONFIRMED,
        ),
        additional_wishes=Field[list[str]](
            value=["Scatter ashes in the Atlantic"],
            status=FieldStatus.CONFIRMED,
        ),
    )

    doc = render_wishes_document(state)
    assert doc.is_complete is True
    assert len(doc.missing_fields) == 0

    assert "Jane Doe" in doc.text
    assert "10 Downing Street, London" in doc.text
    assert "WORLDWIDE" in doc.text
    assert "Alice" in doc.text
    assert "Bob" in doc.text
    assert "James Doe" in doc.text
    assert "brother" in doc.text
    assert "Gold Watch to Alice" in doc.text
    assert "Scatter ashes in the Atlantic" in doc.text
    assert "Document Status: COMPLETE" in doc.text


def test_renderer_no_children_and_no_gifts():
    state = WishesState(
        full_name=Field[str](value="Mark Evans", status=FieldStatus.CONFIRMED),
        home_address=Field[str](value="45 High Street", status=FieldStatus.CONFIRMED),
        covers_worldwide_assets=Field[bool](value=False, status=FieldStatus.CONFIRMED),
        has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
        children=Field[list[str]](status=FieldStatus.NOT_APPLICABLE),
        executor=Executor(
            name=Field[str](value="Sarah Evans", status=FieldStatus.CONFIRMED),
            relationship=Field[str](value="sister", status=FieldStatus.CONFIRMED),
        ),
        specific_gifts=Field[list[Gift]](value=[], status=FieldStatus.CONFIRMED),
        additional_wishes=Field[list[str]](value=[], status=FieldStatus.CONFIRMED),
    )

    doc = render_wishes_document(state)
    assert doc.is_complete is True
    assert "I declare that I have no children." in doc.text
    assert "PRIMARY RESIDENTIAL JURISDICTION" in doc.text
    assert "None specified." in doc.text


def test_renderer_unresolved_contradiction_marks_incomplete():
    state = WishesState(
        full_name=Field[str](value="Jane Doe", status=FieldStatus.CONFIRMED),
        home_address=Field[str](value="10 Downing St", status=FieldStatus.CONFIRMED),
        covers_worldwide_assets=Field[bool](value=True, status=FieldStatus.CONFIRMED),
        has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
        children=Field[list[str]](status=FieldStatus.NOT_APPLICABLE),
        executor=Executor(
            name=Field[str](value="James", status=FieldStatus.CONFIRMED),
            relationship=Field[str](value="brother", status=FieldStatus.CONFIRMED),
        ),
        specific_gifts=Field[list[Gift]](value=[], status=FieldStatus.CONFIRMED),
        additional_wishes=Field[list[str]](value=[], status=FieldStatus.CONFIRMED),
    )

    # If there is a pending contradiction, document must not be marked complete
    doc = render_wishes_document(state, has_pending_clarification=True)
    assert doc.is_complete is False
