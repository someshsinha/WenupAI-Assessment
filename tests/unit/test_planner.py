from app.domain.models import (
    WishesState,
    Field,
    FieldStatus,
    Executor,
    Gift,
    Session,
    PendingClarification,
)
from app.domain.planner import (
    PlannerAction,
    plan_next_action,
    get_missing_fields,
    is_state_complete,
)


def test_planner_initial_action_is_ask_full_name():
    session = Session(id="sess_1")
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.ASK_FULL_NAME


def test_planner_advances_to_next_missing_field():
    session = Session(
        id="sess_2",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
        ),
    )
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.ASK_HOME_ADDRESS


def test_planner_skips_children_when_has_children_is_false():
    session = Session(
        id="sess_3",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
            home_address=Field[str](value="10 Downing St, London", status=FieldStatus.CONFIRMED),
            covers_worldwide_assets=Field[bool](value=True, status=FieldStatus.CONFIRMED),
            has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
            children=Field[list[str]](status=FieldStatus.NOT_APPLICABLE),
        ),
    )
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.ASK_EXECUTOR_NAME


def test_planner_asks_children_names_when_has_children_is_true():
    session = Session(
        id="sess_4",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
            home_address=Field[str](value="10 Downing St, London", status=FieldStatus.CONFIRMED),
            covers_worldwide_assets=Field[bool](value=True, status=FieldStatus.CONFIRMED),
            has_children=Field[bool](value=True, status=FieldStatus.CONFIRMED),
            children=Field[list[str]](status=FieldStatus.UNKNOWN),
        ),
    )
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.ASK_CHILDREN_NAMES


def test_planner_prioritizes_contradiction_over_missing_fields():
    session = Session(
        id="sess_5",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
        ),
        pending_clarification=PendingClarification(
            field="full_name",
            issue_type="contradiction",
            user_statement="Alice Cooper",
            question_to_ask="Did you mean Alice Smith or Alice Cooper?",
        ),
    )
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.RESOLVE_CONTRADICTION
    assert ctx["field"] == "full_name"


def test_planner_prioritizes_unconfirmed_field():
    session = Session(
        id="sess_6",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
            home_address=Field[str](value="12 High St", status=FieldStatus.UNCONFIRMED),
        ),
    )
    action, ctx = plan_next_action(session)
    assert action == PlannerAction.CONFIRM_UNCONFIRMED
    assert ctx["field"] == "home_address"
    assert ctx["value"] == "12 High St"


def test_planner_returns_complete_when_all_fields_confirmed():
    session = Session(
        id="sess_complete",
        state=WishesState(
            full_name=Field[str](value="Alice Smith", status=FieldStatus.CONFIRMED),
            home_address=Field[str](value="12 High St", status=FieldStatus.CONFIRMED),
            covers_worldwide_assets=Field[bool](value=True, status=FieldStatus.CONFIRMED),
            has_children=Field[bool](value=False, status=FieldStatus.CONFIRMED),
            children=Field[list[str]](status=FieldStatus.NOT_APPLICABLE),
            executor=Executor(
                name=Field[str](value="Bob Smith", status=FieldStatus.CONFIRMED),
                relationship=Field[str](value="brother", status=FieldStatus.CONFIRMED),
            ),
            specific_gifts=Field[list[Gift]](value=[], status=FieldStatus.CONFIRMED),
            additional_wishes=Field[list[str]](value=[], status=FieldStatus.CONFIRMED),
        ),
    )
    assert is_state_complete(session.state)
    assert len(get_missing_fields(session.state)) == 0

    action, _ = plan_next_action(session)
    assert action == PlannerAction.COMPLETE
