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


