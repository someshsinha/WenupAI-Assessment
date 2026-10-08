from typing import Any
from datetime import datetime, timezone

from app.domain.models import Session, Message, Change, FieldStatus
from app.domain.reducer import apply_operations_to_session
from app.domain.contradictions import detect_contradictions
from app.domain.planner import plan_next_action, PlannerAction
from app.llm.base import LLMClient
from app.llm.prompts import build_extraction_prompt
from app.llm.composer import ResponseComposer
from app.llm.parsing import extract_with_repair
from app.llm.grounding import filter_grounded_operations


class ConversationService:
    """Orchestrates single-turn conversational workflow across LLM, validation, and domain state."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.composer = ResponseComposer(llm_client=llm_client)

    async def process_user_turn(
        self,
        session: Session,
        user_message: str,
    ) -> tuple[Session, str, list[Change]]:
        """Processes a single conversational turn.
        Returns: (updated_session, assistant_message, changes_produced)
        """
        turn = (len(session.messages) // 2) + 1
        now = datetime.now(timezone.utc)

        # 1. Record incoming user message
        new_session = session.model_copy(deep=True)
        new_session.messages.append(
            Message(role="user", content=user_message, turn=turn, timestamp=now)
        )
        new_session.updated_at = now

        # 2. Build extraction payload
        extraction_payload = {
            "prompt": build_extraction_prompt(
                user_message=user_message,
                current_state=new_session.state.model_dump(),
                pending_clarification=new_session.pending_clarification.model_dump() if new_session.pending_clarification else None,
                recent_history=[m.model_dump() for m in new_session.messages[-4:]],
            ),
            "user_message": user_message,
            "state": new_session.state.model_dump(),
        }

        # 3. Structured LLM Extraction + Repair
        extraction_result, extraction_error = await extract_with_repair(
            self.llm_client, extraction_payload
        )

        initial_change_count = len(new_session.changes)

        if extraction_error or extraction_result is None:
            # Fallback on extraction failure: state unchanged
            fallback_msg = (
                "I apologize, but I couldn't clearly understand that statement. "
                "Could you please repeat or rephrase your answer?"
            )
            new_session.messages.append(
                Message(role="assistant", content=fallback_msg, turn=turn, timestamp=datetime.now(timezone.utc))
            )
            return new_session, fallback_msg, []

        # 4. Evidence Grounding Check
        grounded_ops, ungrounded_ops = filter_grounded_operations(
            extraction_result.operations, user_message
        )

        # 5. Contradiction Detection against confirmed state
        proposed_ops_dicts = [op.model_dump() for op in grounded_ops]
        detected_contradictions = detect_contradictions(
            state=new_session.state,
            operations=proposed_ops_dicts,
            user_message=user_message,
        )

        # Check if model also flagged an explicit contradiction
        if extraction_result.contradictions and not detected_contradictions:
            for ec in extraction_result.contradictions:
                from app.domain.models import PendingClarification
                detected_contradictions.append(
                    PendingClarification(
                        field=ec.field,
                        issue_type="contradiction",
                        user_statement=user_message,
                        conflicting_value=ec.conflicting_value,
                        question_to_ask=ec.explanation or f"Could you clarify the conflicting information regarding {ec.field}?",
                    )
                )

        if detected_contradictions:
            # Contradiction pauses mutation: preserve confirmed state
            new_session.pending_clarification = detected_contradictions[0]
        else:
            # Apply valid grounded operations to session
            if proposed_ops_dicts:
                new_session = apply_operations_to_session(
                    session=new_session,
                    operations=proposed_ops_dicts,
                    turn=turn,
                )

        # 6. Query Deterministic Planner for next required action
        action, action_context = plan_next_action(new_session)

        # 7. Compose Assistant Response via ResponseComposer
        assistant_response = await self.composer.compose_response(
            action=action,
            action_context=action_context,
            recent_messages=new_session.messages,
        )

        # 8. Record assistant message and return
        new_session.messages.append(
            Message(role="assistant", content=assistant_response, turn=turn, timestamp=datetime.now(timezone.utc))
        )
        new_changes = new_session.changes[initial_change_count:]

        return new_session, assistant_response, new_changes

