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
        # Check for correction intent
        has_explicit_correction = bool(re.search(r"\b(correction|mistake|change my|instead of|correct to|modify|update my)\b", user_message, re.I))
        has_soft_correction = bool(re.search(r"\b(actually|in fact)\b", user_message, re.I))
        is_correction = has_explicit_correction or has_soft_correction
        # For sensitive family/children boolean flips, require explicit correction keywords to bypass contradiction detector
        is_children_correction = has_explicit_correction
        user_intent = "correction" if is_correction else "provide_info"

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
            r"(?:i live at|living at|address is|at|moved,?\s*(?:my\s+)?address is)\s+([0-9]+[A-Za-z0-9\s,]+?(?:street|st|road|rd|avenue|ave|lane|london|manchester|uk|drive|dr|way)[A-Za-z0-9\s,]*?)(?=[,\s]+(?:and\b|my\b|i\b|with\b|$)|$|\.)",
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
        elif not any(op["field"] in ("full_name", "home_address") for op in operations) and state.get("home_address", {}).get("status") == "unknown" and state.get("full_name", {}).get("status") in ("confirmed", "unconfirmed"):
            clean_addr = re.sub(r"^(?:i live at|living at|my address is|address is|i live in|in)\s+", "", user_message.strip(), flags=re.I).rstrip(",.")
            # If address is unknown, accept any non-empty string that is not responding to a different field
            if clean_addr and not re.search(r"^(?:yes|no|nope|yeah)\b", clean_addr, re.I) and not re.search(r"\b(children|kids|executor|gifts|wishes|assets)\b", clean_addr, re.I):
                operations.append({
                    "op": "set",
                    "field": "home_address",
                    "value": clean_addr,
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
        no_kids_match = re.search(
            r"(?:i\s+)?(?:don't|do not|haven't got|have no)\s*(?:have\s+)?(?:any\s+)?(?:children|kids)|no\s+(?:children|kids)",
            user_message,
            re.I,
        )
        if no_kids_match:
            operations.append({
                "op": "set",
                "field": "has_children",
                "value": False,
                "evidence": no_kids_match.group(0).strip(),
                "confidence": "high",
                "is_correction": is_children_correction,
            })
        elif re.search(r"\b(a few kids|a few children|some kids)\b", user_message, re.I):
            ambiguities.append({
                "field": "children",
                "evidence": user_message,
                "issue": "Specific number or names of children not provided",
            })
        else:
            kids_match = re.search(
                r"(?:have|got)\s+(?:a|an|\d+|one|two|three|four|five|six|seven|eight|nine|ten)?\s*(?:children|kids|child|sons?|daughters?)(?::\s*|\s+named\s+|\s+called\s+)?([A-Za-z\s,and]+)?",
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
                    "is_correction": is_children_correction,
                })
                names_str = kids_match.group(1)
                if names_str:
                    clean_names = [
                        n.strip()
                        for n in re.split(r",|\band\b", names_str)
                        if n.strip() and not re.search(r"\b(named|called|have|assets|executor|world|live|name|is|actually)\b", n, re.I)
                    ]
                    if clean_names:
                        operations.append({
                            "op": "set",
                            "field": "children",
                            "value": clean_names,
                            "evidence": names_str.strip(),
                            "confidence": "high",
                            "is_correction": is_children_correction,
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
                        "is_correction": is_children_correction,
                    })


        # 5. Executor (Only extract if message is not a specific gift assignment)
        is_gift_stmt = bool(re.search(r"\b(?:leave|give)\s+(?:my\s+)?[^.,\n]+?\s+to\b", user_message, re.I))
        rel_pattern = r"\b(mistress|lover|future wife|future husband|wife|husband|spouse|partner|brother|sister|friend|lawyer|solicitor|mother|father|son|daughter|cousin|uncle|aunt|colleague)\b"
        rel_found = None
        if not is_gift_stmt:
            rel_m = re.search(rel_pattern, user_message, re.I)
            if rel_m:
                rel_found = rel_m.group(1).lower()

        found_name = None
        found_name_ev = user_message

        # Pattern A: Combined relationship + name (e.g. "my brother James Miller", "my spouse Emily", "wife Emily")
        if not is_gift_stmt:
            combo_m = re.search(
                r"(?:my\s+)?" + rel_pattern + r"\s+(?:named\s+|called\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                user_message,
                re.I,
            )
            if combo_m:
                candidate = combo_m.group(2).strip()
                candidate = re.split(r"\s+(?:and|she|he|who|is|as|with)\b", candidate, flags=re.I)[0].strip()
                if not re.search(rel_pattern, candidate, re.I) and not re.search(r"\b(is|as|the|executor|wishes|my|to|of|a|an)\b", candidate, re.I):
                    found_name = candidate
                    found_name_ev = combo_m.group(0)

        # Pattern B: "her name is Emily", "his name is Emily", "executor's name is Emily", "their name is Emily"
        if not found_name and not is_gift_stmt and not re.search(r"\bmy name is\b", user_message, re.I):
            name_m = re.search(
                r"\b(?:her|his|my\s+executor\'s|the\s+executor\'s|executor\'s|their)\s+name\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                user_message,
                re.I,
            )
            if name_m:
                candidate = name_m.group(1).strip()
                candidate = re.split(r"\s+(?:and|she|he|who|is|as|with)\b", candidate, flags=re.I)[0].strip()
                if not re.search(rel_pattern, candidate, re.I) and not re.search(r"\b(is|as|the|executor|wishes|my|to|of|a|an)\b", candidate, re.I):
                    found_name = candidate
                    found_name_ev = name_m.group(0)

        # Pattern C: "appoint Emily as executor", "executor is Emily", "executor: Emily"
        if not found_name and not re.search(r"\bmy name is\b", user_message, re.I):
            exec_m = re.search(
                r"(?:executor is|appoint|executor:\s*)\s+([A-Za-z\s]+?)(?:\s+as\s+(?:the\s+)?executor|\s*$)",
                user_message,
                re.I,
            )
            if exec_m:
                candidate = exec_m.group(1).strip()
                clean_candidate = re.sub(r"^(?:my|the|her|his|our)\s+", "", candidate, flags=re.I).strip()
                clean_candidate = re.split(r"\s+(?:and|she|he|who|is|as|with)\b", clean_candidate, flags=re.I)[0].strip()
                if re.search(r"^" + rel_pattern + r"$", clean_candidate, re.I):
                    if not rel_found:
                        rel_found = clean_candidate.lower()
                elif not re.search(rel_pattern, clean_candidate, re.I) and not re.search(r"\b(is|as|the|executor|wishes|to|of|a|an)\b", clean_candidate, re.I):
                    if clean_candidate and any(c.isupper() for c in clean_candidate):
                        found_name = clean_candidate
                        found_name_ev = exec_m.group(0)

        # Pattern D: "Emily is my executor" or "Bob Smith is my executor"
        if not found_name and not re.search(r"\bmy name is\b", user_message, re.I):
            exec_m2 = re.search(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:is my executor|as executor)",
                user_message,
                re.I,
            )
            if exec_m2:
                candidate = exec_m2.group(1).strip()
                candidate = re.split(r"\s+(?:and|she|he|who|is|as|with)\b", candidate, flags=re.I)[0].strip()
                if not re.search(rel_pattern, candidate, re.I) and not re.search(r"^(?:my|the|her|his|our)\b", candidate, re.I):
                    found_name = candidate
                    found_name_ev = exec_m2.group(0)

        # Pattern E: Standalone capitalized name when executor name is unknown and user is at executor stage (not in turn 1 where full_name is unknown)
        if not found_name and not any(op["field"] in ("full_name", "home_address") for op in operations) and not re.search(r"\bmy name is\b", user_message, re.I) and (
            state.get("executor", {}).get("name", {}).get("status") == "unknown" and
            state.get("full_name", {}).get("status") in ("confirmed", "unconfirmed") and
            state.get("home_address", {}).get("status") in ("confirmed", "unconfirmed")
        ):
            clean_word = user_message.strip().rstrip(",.")
            words = clean_word.split()
            if 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w.isalpha()):
                if not re.search(rel_pattern, clean_word, re.I) and not re.search(r"\b(yes|no|road|street|london|none|executor|wishes|all|nothing)\b", clean_word, re.I):
                    found_name = clean_word
                    found_name_ev = user_message.strip()

        # If providing name for the first time or clarifying, allow updating relationship as well
        rel_is_correction = is_correction
        if found_name and state.get("executor", {}).get("name", {}).get("status") == "unknown":
            rel_is_correction = True

        if found_name:
            operations.append({
                "op": "set",
                "field": "executor.name",
                "value": found_name,
                "evidence": found_name_ev,
                "confidence": "high",
                "is_correction": is_correction,
            })

        if rel_found:
            operations.append({
                "op": "set",
                "field": "executor.relationship",
                "value": rel_found,
                "evidence": user_message,
                "confidence": "high",
                "is_correction": rel_is_correction,
            })

        # 6. Specific Gifts
        if re.search(r"\b(no specific gifts|no gifts|nothing specific|(?:don't|do not) have any specific gifts|no special gifts)\b", user_message, re.I):
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
