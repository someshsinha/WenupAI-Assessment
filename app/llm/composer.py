from typing import Any
from app.domain.planner import PlannerAction
from app.domain.models import Message
from app.llm.base import LLMClient
from app.llm.prompts import build_compose_prompt

DETERMINISTIC_ACTION_TEMPLATES = {
    PlannerAction.ASK_FULL_NAME: "Hello! I will help you create your Personal Wishes Document. To get started, what is your full legal name?",
    PlannerAction.ASK_HOME_ADDRESS: "Thank you. What is your current home address?",
    PlannerAction.ASK_WORLDWIDE_ASSETS: "Got it. Does this document cover your assets worldwide, or only in a specific country?",
    PlannerAction.ASK_HAS_CHILDREN: "Do you have any children?",
    PlannerAction.ASK_CHILDREN_NAMES: "Could you please provide the full names of your children?",
    PlannerAction.ASK_EXECUTOR_NAME: "Who would you like to appoint as the executor of your personal wishes?",
    PlannerAction.ASK_EXECUTOR_RELATIONSHIP: "What is the executor's relationship to you (for example: brother, spouse, friend)?",
    PlannerAction.ASK_SPECIFIC_GIFTS: "Are there any specific gifts or personal items you would like to leave to specific individuals?",
    PlannerAction.ASK_ADDITIONAL_WISHES: "Do you have any additional wishes, funeral preferences, or special instructions to record?",
    PlannerAction.RESOLVE_CONTRADICTION: "Could you please clarify this conflicting information?",
    PlannerAction.CONFIRM_UNCONFIRMED: "Could you confirm this detail so we can proceed?",
    PlannerAction.COMPLETE: "Thank you! All required information for your Personal Wishes Document has been collected. You can review your draft document in the preview pane.",
}


class ResponseComposer:
    """Produces natural conversational responses aligned with planned actions, with fallback templates."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def get_deterministic_fallback(self, action: PlannerAction, context: dict[str, Any]) -> str:
        """Returns deterministic fallback text for an action."""
        if action == PlannerAction.RESOLVE_CONTRADICTION:
            return context.get("question") or DETERMINISTIC_ACTION_TEMPLATES[action]
        if action == PlannerAction.CONFIRM_UNCONFIRMED:
            field_name = context.get("field", "this")
            val = context.get("value", "")
            return f"Just to confirm, you mentioned {field_name}: '{val}'. Is that correct?"
        return DETERMINISTIC_ACTION_TEMPLATES.get(action, "How can I assist you further with your document?")

    async def compose_response(
        self,
        action: PlannerAction,
        action_context: dict[str, Any],
        recent_messages: list[Message] | None = None,
    ) -> str:
        """Generates a natural-language response for the specified planner action."""
        fallback = self.get_deterministic_fallback(action, action_context)

        compose_payload = {
            "prompt": build_compose_prompt(
                action=action.value,
                context=action_context,
                recent_messages=[m.model_dump() for m in recent_messages[-4:]] if recent_messages else [],
            ),
            "action": action.value,
            "context": action_context,
        }

        try:
            response = await self.llm_client.compose(compose_payload)
            if response and response.strip():
                return response.strip()
            return fallback
        except Exception:
            return fallback
