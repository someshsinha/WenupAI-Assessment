# Architectural Decisions & Design Rationale

This document details the architectural decisions, design choices, trade-offs, and production evolution blueprint for the **Wenup Document Intake Assistant**.

---

## 1. System Architecture: Deterministic Domain State Machine vs. Agentic Frameworks

### Decision
We rejected heavy autonomous agent frameworks (e.g., LangGraph, AutoGen, CrewAI) and pure prompt-driven LLM orchestration. Instead, we architected the system around a **Deterministic Domain Engine** with an **LLM-as-Extractor** boundary.

```
                  ┌──────────────────────────────────────────────┐
                  │                 User Turn                    │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          LLM Extraction Layer                │
                  │   (Gemini 2.5 Flash / MockLLMClient)         │
                  └──────────────────────┬───────────────────────┘
                                         │ Structured Operations JSON
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          Evidence Grounding Guard            │
                  │  (Token overlap + Normalization validation)  │
                  └──────────────────────┬───────────────────────┘
                                         │ Validated Operations
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       Contradiction Detection Engine         │
                  │ (Compares proposed values against confirmed) │
                  └──────────────┬───────────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
       (Contradiction Found)             (No Contradiction)
                 ▼                               ▼
  ┌──────────────────────────────┐ ┌──────────────────────────────┐
  │     PendingClarification     │ │    Deterministic Reducer     │
  │  (State mutation paused)     │ │   (Atomic State Mutation)    │
  └──────────────┬───────────────┘ └──────────────┬───────────────┘
                 │                                │
                 │               ┌────────────────┴───────────────┐
                 │               │   Conditional Cascade Rules    │
                 │               │ (has_children -> children N/A) │
                 │               └────────────────┬───────────────┘
                 │                                │
                 ▼                                ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                 Deterministic Planner Engine                 │
  │     (Prioritizes: Contradiction -> Unconfirmed -> Missing)   │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │            Natural Response Composer / Fallback              │
  └──────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                 Deterministic Document Renderer              │
  └──────────────────────────────────────────────────────────────┘
```

### Rationale
1. **Legal Tech Precision**: Estate intake requires strict compliance and zero tolerance for hallucinated state transitions. A deterministic state machine guarantees that every field update adheres to domain constraints.
2. **Auditability & Reproducibility**: Given the exact same sequence of user messages and state transitions, the reducer and planner produce identical states.
3. **Observability**: Clear boundaries between intent extraction, domain validation, state reduction, and natural language composition allow isolated debugging of any anomaly.

---

## 2. State Management: Domain State as the Single Source of Truth

### Decision
The structured `WishesState` object (with `Field[T]` containers tracking `value`, `status`, `evidence`, and `turn`) is the **single source of truth**. Conversation history is treated as evidence and audit log, never as the runtime state representation.

### Field Lifecycle States
- `UNKNOWN`: The field has never been provided or confirmed.
- `UNCONFIRMED`: A value was extracted with low-to-medium confidence or inferred, requiring user confirmation.
- `CONFIRMED`: Explicitly provided or confirmed by the user.
- `NOT_APPLICABLE`: Explicitly excluded by domain cascades (e.g., `children` when `has_children=False`).

### Trade-offs
- *Pros*: Eliminates state drift across multi-turn dialogues; avoids re-parsing long conversation histories.
- *Cons*: Requires explicit domain schema definition and cascade handlers for every conditional field.

---

## 3. LLM Extraction & Grounding Boundaries

### Decision
1. **Strict JSON Output**: The LLM is instructed to output purely structured JSON operations (`op`, `field`, `value`, `evidence`, `is_correction`).
2. **Evidence Grounding Filter (`app/llm/grounding.py`)**:
   - Strips whitespace and punctuation.
   - Computes token overlap between extracted evidence and the **current user turn only**.
   - Drops any hallucinated operation where evidence cannot be grounded in the user's latest statement.
3. **1-Attempt JSON Repair Flow (`app/llm/parsing.py`)**:
   - If the LLM returns invalid JSON or Markdown fences, the system attempts regex extraction and a single repair prompt. If that fails, it safely falls back to a deterministic asking response without corrupting state.

---

## 4. Contradiction Detection vs. Explicit Correction

### Decision
An unacknowledged conflict is **never** treated as a silent overwrite:
- **Contradiction**: When proposed information conflicts with a `CONFIRMED` field and the user did not include explicit correction directives (e.g., `correction`, `mistake`, `change my`).
  - *Action*: State mutation is paused; a `PendingClarification(issue_type="contradiction")` is attached to the session; the planner prioritizes resolving the contradiction.
- **Correction**: When the user explicitly signals an update (`is_correction=True`) or directly invokes `PATCH /api/sessions/{id}/state`.
  - *Action*: The reducer updates the field, clears any active `PendingClarification` for that field, and logs `Change(kind="correction")` in the change history.

---

## 5. Conditional Cascades & Rules Engine

### Decision
Domain dependencies are evaluated deterministically in `app/domain/rules.py` immediately following reducer state changes:
1. `has_children = False` $\rightarrow$ sets `children.status = NOT_APPLICABLE` and `children.value = None`.
2. `has_children = True` (after being `False`) $\rightarrow$ resets `children.status = UNKNOWN` and prompts for children's names.
3. Explicit "no specific gifts" or "no additional wishes" $\rightarrow$ sets value to `[]` with status `CONFIRMED` (differentiating an explicitly empty list from `UNKNOWN`).

---

## 6. Document Generation: Deterministic Rendering vs. LLM Generation

### Decision
Final documents are generated using a deterministic Jinja2/string templating engine (`app/docgen/renderer.py`) rather than prompt-based LLM generation.

### Rationale
- **Legal Compliance**: Mandatory legal disclaimers (*"THIS DOCUMENT CONSTITUTES AN INFORMAL RECORD OF PERSONAL WISHES ONLY AND IS NOT A LEGALLY BINDING WILL OR TESTAMENT"*) must never be omitted, altered, or hallucinated.
- **Completeness Enforcement**: Incomplete fields are rendered as explicit placeholders `[UNSPECIFIED]`, with document status set to `incomplete` until all mandatory fields are confirmed.

---

## 7. Concurrency & Session Isolation

### Decision
- In-memory `SessionStore` (`app/services/session_store.py`) assigns an `asyncio.Lock` to each active session ID.
- Concurrent requests to the *same* session are serialized to prevent race conditions during reducer state mutations.
- Concurrent requests across *different* sessions execute independently without contention.

---

## 8. Production Readiness Roadmap

| Area | Current Implementation | Production Target |
| :--- | :--- | :--- |
| **Persistence** | In-memory `SessionStore` with per-session async locks | PostgreSQL event-sourcing store with JSONB snapshots & row-level locking |
| **Distributed Locking** | Process-local `asyncio.Lock` | Redis distributed lock (`Redlock`) with lease timeout |
| **Authentication & AuthZ** | Open session IDs | JWT-based OAuth2 / OIDC with tenant and user session isolation |
| **LLM Gateway** | Google GenAI SDK (`GeminiClient`) with `MockLLMClient` fallback | Circuit-breaker LLM gateway (LiteLLM / custom proxy) with automated retry & rate limiting |
| **Observability** | Structured logging in FastAPI | OpenTelemetry distributed tracing, Prometheus metrics, and Langfuse / Arize Phoenix LLM monitoring |
| **Encryption** | Memory transient | AES-256 field-level encryption for PII and sensitive estate wishes at rest |
