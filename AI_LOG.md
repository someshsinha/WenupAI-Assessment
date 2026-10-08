# AI Development & Decision Log

This log captures key prompts, architectural decisions, what was questioned, iterations, and deliberate engineering judgments throughout the development of the **Document Intake Assistant**.

---

## Log Entry 001 — Project Inception & Implementation Strategy

### Prompt / Task
Review the Wenup Technical Test Assignment, Revised PRD v2, and Feature-by-Feature Implementation & Testing Guide v2. Establish repository rules, strict feature-by-feature execution protocol (`IMPLEMENT → MANUAL CHECK → WRITE TESTS → ALL PASS → COMMIT → NEXT FEATURE`), and ensure no scope creep or framework bloat.

### Output that was useful
- Feature breakdown from F01 to F26.
- Architecture defining LLM for language extraction vs deterministic domain layer for state, planning, and document rendering.
- Defined 8 golden failure/edge scenarios.

### What I questioned
- *Should we use LangGraph or an agent framework?*
  **Answer**: No. PRD explicitly rejects LangGraph for this assignment. Explicit Python orchestration, Pydantic schemas, and a deterministic reducer are clearer, more testable, and less prone to uncontrolled loops.
- *Should the LLM return the whole new state or state operations?*
  **Answer**: LLM returns operations with grounded evidence (`op`, `field`, `value`, `evidence`). Domain reducer validates and mutates state. This prevents model hallucinations from corrupting application state.
- *Should document preview be LLM-generated?*
  **Answer**: No. Document generation must be 100% deterministic based only on confirmed structured state, with explicit legal disclaimers.

### Decision
Follow the exact build order:
- **Phase 1: Core Engine** (F01–F14)
- **Phase 2: API, Sessions & Concurrency** (F15–F17)
- **Phase 3: Functional Frontend** (F18–F22)
- **Phase 4: Testing, Evaluation & Submission** (F23–F26)

Proceed feature-by-feature, validating with tests and commits at each step.

---

## Log Entry 002 — F01 Project Foundation

### Prompt / Task
Implement F01: FastAPI application skeleton, Pydantic settings configuration (`app/config.py`), `.env.example`, dependencies (`requirements.txt`), and health endpoint (`GET /api/health`).

### Output that was useful
- Clean FastAPI application structure with environment variable management via `pydantic-settings`.
- Health endpoint reporting uptime status, configuration mode (`mock` by default), and timestamp.

### What I questioned
- *Should we include heavy optional dependencies like `uvloop` in `requirements.txt`?*
  **Answer**: No. `uvloop` slowed down installation and added unnecessary native build complexity. Standard Python asyncio + `uvicorn` is fast, portable, and cleanly satisfies the requirements.

### Decision
Use standard `uvicorn` and pure-Python async client testing with `httpx` + `pytest-asyncio`.

### Result
- Application boots cleanly.
- `GET /api/health`, `/`, and `/docs` all return HTTP 200.
- All 3 tests in `tests/test_health.py` pass.

---

## Log Entry 003 — F02 Domain State Model

### Prompt / Task
Implement F02: Structured source of truth in `app/domain/models.py` using explicit `FieldStatus` (`UNKNOWN`, `UNCONFIRMED`, `CONFIRMED`, `NOT_APPLICABLE`) and strongly typed models for all assignment fields, changes, clarifications, and sessions.

### Output that was useful
- Explicit `Field[T]` generic model capturing value, status, evidence, and turn.
- Models for `Executor`, `Gift`, `WishesState`, `Change`, `PendingClarification`, `Message`, and `Session`.

### What I questioned
- *Should conversation history hold the current state values?*
  **Answer**: No. PRD guardrail states conversation history is strictly evidence/audit context. `WishesState` is the sole source of truth.

### Decision
Model all fields explicitly in `WishesState` and track mutations via immutable `Change` audit logs.

### Result
- Domain models created with clear status transitions.
- All 7 new unit tests in `tests/unit/test_domain_models.py` passed (10/10 total tests pass).

---

## Log Entry 004 — F03 State Reducer + Validation

### Prompt / Task
Implement F03: Single deterministic state reducer in `app/domain/reducer.py` with validation rules in `app/domain/validators.py`. Support `set`, `add`, `remove`, `clear`, `confirm` across all whitelisted fields with strict type checking and change auditing.

### Output that was useful
- Whitelist-driven validation (`ALLOWED_FIELDS`) rejecting unauthorized paths and illegal operations before state changes occur.
- Immutable state copies (`model_copy(deep=True)`) preventing unintended mutations.
- Batch atomic execution (`apply_operations`).

### What I questioned
- *How should item deletion from complex lists like `specific_gifts` work when a user only specifies the item name?*
  **Answer**: Allow `remove` operation on `specific_gifts` to accept either full `Gift` dicts or string item names (e.g. `"Vintage Guitar"`).

### Decision
Support string identifiers for `remove` operations in list fields and ensure idempotent `set` operations do not create redundant change records.

### Result
- 9 unit tests created in `tests/unit/test_reducer.py` verifying field acceptance, unknown field rejection, type mismatches, and immutability.
- All 19 tests in the test suite pass.

---

## Log Entry 005 — F04 Explicit Correction Semantics

### Prompt / Task
Implement F04: Handle explicit user corrections (e.g., "Actually, Bob is my executor, not James"), replace confirmed values directly without getting stuck in clarification loops, record audit events with `kind="correction"`, and clear active pending clarifications.

### Output that was useful
- Clean separation between normal `set` operations and `correction` mutations.
- `apply_operations_to_session` helper that clears pending clarification once the referenced field is updated or corrected.

### What I questioned
- *Should an explicit correction require confirmation before being accepted?*
  **Answer**: No. An explicit correction from the user is direct intent. Requiring confirmation would create an unnecessary clarification loop. It should immediately replace the value and record the old vs new values in the change log.

### Decision
Apply corrections immediately, record `kind="correction"` with `old_value` and `new_value`, and clear pending clarifications for that field.

### Result
- 3 new unit tests in `tests/unit/test_corrections.py` covering scalar corrections, nested structure corrections, and session-level clarification resolution.
- All 22 tests pass.

---

## Log Entry 006 — F05 Contradiction Handling

### Prompt / Task
Implement F05: Contradiction detection engine in `app/domain/contradictions.py`. Ensure unacknowledged conflicting statements against confirmed state (e.g. `has_children=False` vs mentioning a son/daughter) do not silently overwrite confirmed facts, but instead generate a `PendingClarification` and pause field progression.

### Output that was useful
- `detect_contradictions` inspecting proposed operations and user text against confirmed state.
- Distinct handling where `is_correction=True` allows direct updates while `is_correction=False` on conflicting fields triggers clarification.

### What I questioned
- *Should a semantic mention like 'leave my car to my son' be caught if the LLM didn't emit a `children` operation?*
  **Answer**: Yes. Cross-referencing child-related keywords when `has_children` is confirmed `False` prevents silent inconsistency in the final document.

### Decision
Enforce strict contradiction protection: keep confirmed state unchanged, create `PendingClarification`, and require explicit user resolution before changing the underlying fact.

### Result
- 4 unit tests created in `tests/unit/test_contradictions.py`.
- All 26 tests in the test suite pass.

---

## Log Entry 007 — F06 Conditional State Rules

### Prompt / Task
Implement F06: Conditional state rules and cascades in `app/domain/rules.py` (e.g., `has_children=False` cascades `children` to `NOT_APPLICABLE`, while `has_children=True` resets `children` to `UNKNOWN` if missing; explicitly confirmed empty lists for "no gifts" vs `UNKNOWN`).

### Output that was useful
- Pure function `apply_conditional_rules(state: WishesState)` seamlessly incorporated into the reducer pipeline.
- Distinction between `UNKNOWN` (must be prompted) and `CONFIRMED` empty list `[]` (user deliberately stated "no gifts").

### What I questioned
- *If the user corrects `has_children` from `False` back to `True`, what happens to `children`?*
  **Answer**: `children` must automatically transition from `NOT_APPLICABLE` back to `UNKNOWN` so the planner can ask for the children's names.

### Decision
Enforce deterministic rule cascades post-operation so invalid state combinations (e.g. `has_children=False` with `children` remaining `UNKNOWN`) are impossible.

### Result
- 5 unit tests in `tests/unit/test_rules.py` covering all cascades and empty list transitions.
- All 31 tests pass.

---

## Log Entry 008 — F07 Deterministic Planner

### Prompt / Task
Implement F07: Deterministic Planner in `app/domain/planner.py` to decide **WHAT** action happens next (resolving contradictions, confirming unconfirmed fields, asking for missing fields in strict order, or completing the document).

### Output that was useful
- `PlannerAction` enum representing all valid workflow actions.
- Priority engine: `RESOLVE_CONTRADICTION` $\rightarrow$ `CONFIRM_UNCONFIRMED` $\rightarrow$ Next missing field $\rightarrow$ `COMPLETE`.
- Helpers `get_missing_fields` and `is_state_complete`.

### What I questioned
- *Should the LLM decide which field to ask next?*
  **Answer**: No. Deterministic planner owns workflow decisions. This guarantees zero skipped required fields, no hallucinated steps, and predictable interview flow.

### Decision
Keep planner logic 100% deterministic outside the LLM. The LLM will only be responsible for phrasing (F13).

### Result
- 7 unit tests created in `tests/unit/test_planner.py`.
- All 38 tests in the test suite pass.

---

## Log Entry 009 — F08 LLM Interface + Mock Provider

### Prompt / Task
Implement F08: LLM provider abstraction in `app/llm/base.py`, deterministic offline `MockLLMClient` in `app/llm/mock.py`, and `GeminiClient` in `app/llm/gemini.py`. Ensure the entire suite can run without live API keys and errors map to typed application exceptions.

### Output that was useful
- `LLMClient` Protocol defining `extract` and `compose`.
- `MockLLMClient` with pattern-based extraction for all intake fields, scriptable responses, and error simulations.
- `GeminiClient` with timeout handling and error mapping (`LLMNotConfiguredError`, `LLMProviderError`, `LLMTimeoutError`).

### What I questioned
- *Should tests require network access or a live Gemini API key?*
  **Answer**: No. The PRD explicitly requires deterministic offline testing via `MockLLMClient`. Live keys are purely optional for real-world execution.

### Decision
Use `MockLLMClient` as the default test and development client so the application works out-of-the-box without setup barriers.

### Result
- 6 unit tests in `tests/unit/test_llm_clients.py` verifying mock extraction, composing, scripted errors, and unconfigured Gemini key behavior.
- All 44 tests pass.

---

## Log Entry 010 — F09 Structured LLM Extraction

### Prompt / Task
Implement F09: Strict structured LLM extraction schema (`ExtractionResult`, `ExtractionOperation`, `ExtractionAmbiguity`, `ExtractionContradiction`) in `app/llm/schemas.py` and structured extraction prompts in `app/llm/prompts.py` with prompt-injection defense boundaries.

### Output that was useful
- Pydantic models validating `op`, `field`, `value`, `evidence`, `confidence`, and `is_correction` before operations reach the domain reducer.
- Security instructions in prompts ensuring user messages are treated strictly as passive data.

### What I questioned
- *What if the LLM produces extra fields or invalid operation names?*
  **Answer**: Strict Pydantic validation rejects the schema and triggers the recovery flow (F11) rather than letting invalid data pollute state.

### Decision
Treat LLM output as untrusted external input and enforce strict schema parsing with evidence grounding requirements.

### Result
- 4 unit tests in `tests/unit/test_extraction_schemas.py` verifying valid schemas and rejection of malformed operations.
- All 48 tests pass.

---

## Log Entry 011 — F10 Evidence Grounding Validation

### Prompt / Task
Implement F10: Robust evidence grounding validator in `app/llm/grounding.py`. Verify that all extracted operations reference genuine evidence present in the current user turn, normalize whitespace/case/punctuation, and reject/quarantine fabricated or stale evidence.

### Output that was useful
- `normalize_text` for punctuation and whitespace collapse.
- `is_evidence_grounded` combining exact substring match and token overlap ratio.
- `filter_grounded_operations` to quarantine ungrounded operations.

### What I questioned
- *What if the user says 'Jane Smith.' and the model extracts 'Jane Smith'?*
  **Answer**: Punctuation-agnostic normalization ensures valid responses aren't rejected due to trailing periods, commas, or extra whitespace.
- *What if the model extracts evidence from a previous conversational turn?*
  **Answer**: Grounding strictly validates against the *current* user turn, preventing old statements from re-triggering mutations without current intent.

### Decision
Quarantine any operation whose evidence fails grounding against the current user message, leaving state untouched.

### Result
- 6 unit tests in `tests/unit/test_grounding.py` covering exact matches, punctuation/whitespace normalization, token overlap, and rejection of fabricated/stale evidence.
- All 54 tests pass.

---

## Log Entry 012 — F11 Robust LLM Response Parsing + Recovery

### Prompt / Task
Implement F11: Single parsing utility in `app/llm/parsing.py` supporting Markdown code fence stripping, JSON extraction from surrounding text, Pydantic validation, and a single-retry repair loop with safe failure containment.

### Output that was useful
- `extract_json_from_text` isolating clean JSON from Markdown fences and commentary.
- `extract_with_repair` giving the LLM one opportunity to correct malformed output with error details before safely aborting.

### What I questioned
- *What happens if the second LLM response is also malformed?*
  **Answer**: Return `(None, error)` cleanly so the conversation service leaves state unchanged and responds with a friendly retry message. Never allow a partial or corrupted state mutation.

### Decision
Enforce a 2-strike parsing policy: attempt 1 $\rightarrow$ repair attempt 2 $\rightarrow$ friendly fallback if still failing.

### Result
- 6 unit tests in `tests/unit/test_parsing_recovery.py` verifying plain JSON, code fences, text commentary, repair success, and safe two-failure handling.
- All 60 tests pass.

---

## Log Entry 013 — F12 Conversation Service

### Prompt / Task
Implement F12: Turn orchestration service in `app/services/conversation.py`. Wire together incoming messages, extraction + repair, evidence grounding, contradiction checks, deterministic reducer state updates, planner action selection, response composition, and safe fallback containment.

### Output that was useful
- Clean orchestrator pipeline managing the complete turn boundary.
- Multiple fields in a single message captured atomically in one turn.
- Contradiction detection pausing mutations and preserving confirmed state.

### What I questioned
- *If extraction fails completely due to invalid JSON or LLM provider errors, how should the conversation recover?*
  **Answer**: Leave state untouched (0 changes), record the turn cleanly, and return a polite fallback asking the user to repeat or rephrase.

### Decision
Keep the domain reducer and planner completely decoupled from I/O and LLM providers; `ConversationService` serves as the single orchestrator.

### Result
- 5 integration tests in `tests/unit/test_conversation_service.py` verifying multi-field intake, contradiction pause, corrections, malformed response handling, and provider error safety.
- All 65 tests pass.












