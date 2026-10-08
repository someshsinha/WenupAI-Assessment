import json
import re
from typing import Any
from app.llm.base import LLMError, LLMProviderError


class MockLLMClient:
    """Deterministic, offline LLM mock implementation for tests and local development."""

    def __init__(self):
        self.scripted_extraction: str | None = None
        self.scripted_compose: str | None = None
        self.simulate_error: Exception | None = None

    async def extract(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any] | None = None,
    ) -> str:
        if self.simulate_error:
            raise self.simulate_error

        if self.scripted_extraction is not None:
            return self.scripted_extraction


        user_message = payload.get("user_message", "").strip()
        state = payload.get("state", {})

        operations = []
        ambiguities = []
        contradictions = []
        user_intent = "provide_info"

        # Check for explicit correction intent
        is_correction = bool(re.search(r"\b(actually|correction|change my|instead of|mistake|correct to)\b", user_message, re.I))
        if is_correction:
            user_intent = "correction"

        # 1. Full name detection
        name_match = re.search(
            r"(?:my name is|i am|name is|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*?)(?=[,\s]+(?:and\b|living\b|live\b|my\b|i\b|at\b|[0-9]|$|\.))",
            user_message,
            re.I,
        )
        if not name_match:
            name_match = re.search(r"(?:my name is|i am|name is|i'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", user_message, re.I)

        if name_match:
            val = name_match.group(1).strip().rstrip(",.")
            if len(val.split()) >= 2:
                operations.append({
                    "op": "set",
                    "field": "full_name",
                    "value": val,
                    "evidence": name_match.group(0),
                    "confidence": "high",
                    "is_correction": is_correction,
                })
        elif not any(op["field"] == "full_name" for op in operations) and state.get("full_name", {}).get("status") == "unknown":
            # If standalone 2-3 word capitalized name
            words = user_message.split()
            if 2 <= len(words) <= 3 and all(w[0].isupper() for w in words if w.isalpha()) and not re.search(r"\b(road|street|avenue|london|yes|no)\b", user_message, re.I):
                operations.append({
                    "op": "set",
                    "field": "full_name",
                    "value": user_message.strip(),
                    "evidence": user_message.strip(),
                    "confidence": "high",
                    "is_correction": is_correction,
                })

        # 2. Address detection
        addr_match = re.search(
            r"(?:i live at|living at|address is|at)\s+([0-9]+[A-Za-z0-9\s,]+?(?:street|st|road|rd|avenue|ave|lane|london|manchester|uk|drive|dr|way)[A-Za-z0-9\s,]*?)(?=[,\s]+(?:and\b|my\b|i\b|with\b|$|\.))",
            user_message,
            re.I,
        )
        if addr_match:
            val = addr_match.group(1).strip().rstrip(",.")
            operations.append({
                "op": "set",
                "field": "home_address",
                "value": val,
                "evidence": addr_match.group(0),
                "confidence": "high",
                "is_correction": is_correction,
            })
        elif not any(op["field"] == "home_address" for op in operations) and state.get("home_address", {}).get("status") == "unknown":
            if re.search(r"\b\d+\s+[A-Za-z0-9\s,]+", user_message) and re.search(r"\b(street|st|road|rd|avenue|ave|lane|london|drive|dr|way|uk)\b", user_message, re.I):
                operations.append({
                    "op": "set",
                    "field": "home_address",
                    "value": user_message.strip().rstrip(",."),
                    "evidence": user_message.strip(),
                    "confidence": "high",
                    "is_correction": is_correction,
                })


        # 3. Worldwide assets
        if re.search(
            r"\b(worldwide|around the world|across the world|global|globally|all over the world|international|multiple countries|covers worldwide|global assets|all my assets worldwide)\b",
            user_message,
            re.I,
        ) or (
            state.get("covers_worldwide_assets", {}).get("status") == "unknown"
            and re.search(r"\b(yes|worldwide|globally|yes it does)\b", user_message, re.I)
            and not re.search(r"\b(no|uk only|only uk|local only)\b", user_message, re.I)
        ):
            ev_match = re.search(
                r"(?:assets\s+(?:around the world|across the world|worldwide|globally|in multiple countries)|(?:covers\s+)?worldwide|around the world|across the world|global|globally|all over the world|international)",
                user_message,
                re.I,
            )
            operations.append({
                "op": "set",
                "field": "covers_worldwide_assets",
                "value": True,
                "evidence": ev_match.group(0) if ev_match else user_message,
                "confidence": "high",
                "is_correction": is_correction,
            })
        elif re.search(r"\b(only uk|uk only|not worldwide|just uk|no worldwide|local only)\b", user_message, re.I) or (
            state.get("covers_worldwide_assets", {}).get("status") == "unknown" and re.search(r"\b(no|nope|negative)\b", user_message, re.I)
        ):
            operations.append({
                "op": "set",
                "field": "covers_worldwide_assets",
                "value": False,
                "evidence": user_message,
                "confidence": "high",
                "is_correction": is_correction,
            })

        # 4. Children
        if re.search(r"\b(no children|no kids|don't have children|do not have any children|haven't got children|have no kids|have no children)\b", user_message, re.I):
            operations.append({
                "op": "set",
                "field": "has_children",
                "value": False,
                "evidence": user_message,
                "confidence": "high",
                "is_correction": is_correction,
            })
        elif re.search(r"\b(a few kids|a few children|some kids)\b", user_message, re.I):
            ambiguities.append({
                "field": "children",
                "evidence": user_message,
                "issue": "Specific number or names of children not provided",
            })
        else:
            kids_match = re.search(
                r"(?:have|got)\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)?\s*(?:children|kids|child|sons?|daughters?)(?::\s*|\s+named\s+|\s+called\s+)?([A-Za-z\s,and]+)?",
                user_message,
                re.I,
            )
            if kids_match:
                operations.append({
                    "op": "set",
                    "field": "has_children",
                    "value": True,
                    "evidence": kids_match.group(0).strip(),
                    "confidence": "high",
                    "is_correction": is_correction,
                })
                names_str = kids_match.group(1)
                if names_str:
                    clean_names = [
                        n.strip()
                        for n in re.split(r",|\band\b", names_str)
                        if n.strip() and not re.search(r"\b(named|called|have|assets|executor|world|live|name|is)\b", n, re.I)
                    ]
                    if clean_names:
                        operations.append({
                            "op": "set",
                            "field": "children",
                            "value": clean_names,
                            "evidence": names_str.strip(),
                            "confidence": "high",
                            "is_correction": is_correction,
                        })
            elif state.get("has_children", {}).get("value") is True and state.get("children", {}).get("status") == "unknown":
                clean_names = [n.strip() for n in re.split(r",|\band\b", user_message) if n.strip() and n.strip().isalpha()]
                if clean_names:
                    operations.append({
                        "op": "set",
                        "field": "children",
                        "value": clean_names,
                        "evidence": user_message,
                        "confidence": "high",
                        "is_correction": is_correction,
                    })

        # 5. Executor
        exec_match = re.search(r"(?:my\s+)?(brother|sister|friend|spouse|wife|husband|partner|lawyer|mother|father|son|daughter)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", user_message, re.I)
        if exec_match:
            rel = exec_match.group(1).lower()
            name = exec_match.group(2).strip()
            operations.append({
                "op": "set",
                "field": "executor.name",
                "value": name,
                "evidence": exec_match.group(0),
                "confidence": "high",
                "is_correction": is_correction,
            })
            operations.append({
                "op": "set",
                "field": "executor.relationship",
                "value": rel,
                "evidence": exec_match.group(0),
                "confidence": "high",
                "is_correction": is_correction,
            })
        else:
            exec_name_match = re.search(r"(?:executor is|appoint|executor:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", user_message, re.I)
            if not exec_name_match:
                # E.g. "Actually, Bob Smith is my executor"
                exec_name_match2 = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:is my executor|as executor)", user_message, re.I)
                if exec_name_match2:
                    exec_name_match = exec_name_match2

            if exec_name_match:
                operations.append({
                    "op": "set",
                    "field": "executor.name",
                    "value": exec_name_match.group(1).strip(),
                    "evidence": exec_name_match.group(0),
                    "confidence": "high",
                    "is_correction": is_correction,
                })
            elif state.get("executor", {}).get("name", {}).get("status") == "unknown" and re.search(r"\b(brother|sister|friend|spouse|wife|husband|partner|son|daughter)\b", user_message, re.I):
                rel_word = re.search(r"\b(brother|sister|friend|spouse|wife|husband|partner|son|daughter)\b", user_message, re.I).group(1).lower()
                operations.append({
                    "op": "set",
                    "field": "executor.relationship",
                    "value": rel_word,
                    "evidence": user_message,
                    "confidence": "high",
                    "is_correction": is_correction,
                })

        # 6. Specific Gifts
        if re.search(r"\b(no specific gifts|no gifts|nothing specific|don't have any specific gifts|no special gifts)\b", user_message, re.I):
            operations.append({
                "op": "set",
                "field": "specific_gifts",
                "value": [],
                "evidence": user_message,
                "confidence": "high",
                "is_correction": is_correction,
            })
        else:
            gift_match = re.search(r"(?:leave|give)\s+(?:my\s+)?([^.,\n]+?)\s+to\s+([^.,\n]+)", user_message, re.I)
            if gift_match:
                item = gift_match.group(1).strip()
                recipient = gift_match.group(2).strip()
                operations.append({
                    "op": "add",
                    "field": "specific_gifts",
                    "value": {"item": item, "recipient": recipient},
                    "evidence": gift_match.group(0),
                    "confidence": "high",
                    "is_correction": is_correction,
                })

        # 7. Additional Wishes
        if re.search(r"\b(no additional wishes|no other wishes|nothing else|no wishes|that is all|that's all)\b", user_message, re.I):
            operations.append({
                "op": "set",
                "field": "additional_wishes",
                "value": [],
                "evidence": user_message,
                "confidence": "high",
                "is_correction": is_correction,
            })
        elif re.search(r"\b(wish|wishes|funeral|cremat|burial|bury|scatter|ashes|ceremony|memorial|special instruction)\b", user_message, re.I):
            operations.append({
                "op": "add",
                "field": "additional_wishes",
                "value": user_message.strip(),
                "evidence": user_message.strip(),
                "confidence": "high",
                "is_correction": is_correction,
            })


        return json.dumps({
            "user_intent": user_intent,
            "operations": operations,
            "ambiguities": ambiguities,
            "contradictions": contradictions,
        })

    async def compose(self, payload: dict[str, Any]) -> str:
        if self.simulate_error:
            err = self.simulate_error
            self.simulate_error = None
            raise err

        if self.scripted_compose is not None:
            res = self.scripted_compose
            self.scripted_compose = None
            return res

        action = payload.get("action", "COMPLETE")
        context = payload.get("context", {})

        templates = {
            "ASK_FULL_NAME": "Hello! I will help you create your Personal Wishes Document. To begin, could you please provide your full legal name?",
            "ASK_HOME_ADDRESS": "Thank you. What is your current home address?",
            "ASK_WORLDWIDE_ASSETS": "Got it. Does this document cover your assets worldwide, or only in a specific country?",
            "ASK_HAS_CHILDREN": "Thank you. Do you have any children?",
            "ASK_CHILDREN_NAMES": "Could you please list the names of your children?",
            "ASK_EXECUTOR_NAME": "Who would you like to appoint as the executor of your personal wishes?",
            "ASK_EXECUTOR_RELATIONSHIP": "What is the executor's relationship to you (for example: brother, spouse, friend)?",
            "ASK_SPECIFIC_GIFTS": "Are there any specific gifts or personal items you would like to leave to specific individuals?",
            "ASK_ADDITIONAL_WISHES": "Do you have any additional wishes, funeral preferences, or special instructions you would like recorded?",
            "RESOLVE_CONTRADICTION": context.get("question", "Could you please clarify this conflicting information?"),
            "CONFIRM_UNCONFIRMED": f"Just to confirm, you mentioned {context.get('field', 'this')}: {context.get('value')}. Is that correct?",
            "COMPLETE": "Thank you! All required information for your fictional Personal Wishes Document has been captured. You can review your draft document in the preview pane.",
        }

        return templates.get(action, "How can I assist you with your document wishes?")
