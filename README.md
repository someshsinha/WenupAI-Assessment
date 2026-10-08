# Wenup Document Intake Assistant 📝🤖

An AI-assisted, state-machine driven conversational intake system designed for reliable personal wishes and estate document generation. Built with Python 3.12+, FastAPI, Google Gemini 2.5 Flash, and Vanilla JavaScript/CSS.

---

## 🌟 Key Highlights & Design Philosophy

1. **Deterministic Domain State Machine**: The core conversation state (`WishesState`) and domain logic are 100% deterministic. The LLM extracts intent and operations, but domain validators, rules cascades, and state reducers govern all mutations.
2. **Strict Evidence Grounding**: Every extracted operation requires token-level grounding evidence from the user's latest message turn. Ungrounded operations and hallucinations are automatically filtered out.
3. **Contradiction vs. Correction Semantics**:
   - **Contradiction**: Unacknowledged conflicting statements pause state mutations, create a `PendingClarification`, and prompt the user for clarification without overwriting confirmed state.
   - **Correction**: Explicit user corrections (`kind="correction"`) or manual overrides update state immediately with full audit logging.
4. **Conditional Cascades**: Domain dependencies (e.g., `has_children=False` $\rightarrow$ `children=NOT_APPLICABLE`) update atomically upon state changes.
5. **Deterministic Document Generation**: Documents are rendered via structured templating with legally mandated disclaimers rather than probabilistic LLM generation.
6. **Pluggable Architecture**: Seamlessly switch between zero-config offline `MockLLMClient` (for local tests/evaluation) and live `GeminiClient` via `google-genai`.

---

## 🏗️ Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │          FastAPI Web App             │
                      │  (Three-Column Vanilla UI & REST API)│
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    SessionStore (asyncio.Lock)       │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │         ConversationService          │
                      └───────┬──────────────────────┬───────┘
                              │                      │
                   (LLM Extraction)         (Domain Validation)
                              ▼                      ▼
  ┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
  │  LLM Client (Gemini / MockLLM)      │  │  Evidence Grounding Validator       │
  │  - JSON Schema enforcement          │  │  - Normalization & token overlap    │
  │  - 1-Attempt Repair Flow            │  │  - Anti-hallucination filter        │
  └─────────────────────────────────────┘  └──────────────────┬──────────────────┘
                                                              │
                                                              ▼
                                           ┌─────────────────────────────────────┐
                                           │  Contradiction Detection Engine     │
                                           │  - Compares proposed vs confirmed   │
                                           │  - Pauses mutation on conflict      │
                                           └──────────────────┬──────────────────┘
                                                              │
                                                              ▼
                                           ┌─────────────────────────────────────┐
                                           │  Deterministic State Reducer        │
                                           │  - Atomic mutation & audit logging  │
                                           │  - Conditional Cascade Rules        │
                                           └──────────────────┬──────────────────┘
                                                              │
                                                              ▼
                                           ┌─────────────────────────────────────┐
                                           │  Deterministic Planner Engine       │
                                           │  - Resolves contradictions first    │
                                           │  - Prompts missing mandatory fields │
                                           └──────────────────┬──────────────────┘
                                                              │
                                                              ▼
                                           ┌─────────────────────────────────────┐
                                           │  Deterministic Document Renderer    │
                                           │  - Mandatory Legal Disclaimers      │
                                           │  - Completion status tracker        │
                                           └─────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.12+ (or Python 3.14)
- Git

### 1. Installation & Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-username/WenupAI.git
cd WenupAI

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Default `.env` configuration:
```env
APP_NAME="Document Intake Assistant"
APP_ENV=development
LLM_PROVIDER=mock          # Options: "mock" (default, offline) or "gemini"
GEMINI_API_KEY=           # Required if LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### 3. Running the Test Suite

Run the full test suite (98 unit, integration, and scenario tests):

```bash
.venv/bin/pytest -v
```

Run specific test modules:
```bash
# Golden end-to-end scenarios
.venv/bin/pytest -v tests/scenarios/test_golden_scenarios.py

# Integration API tests
.venv/bin/pytest -v tests/integration/

# Unit tests
.venv/bin/pytest -v tests/unit/
```

### 4. Running the Development Server

Start the FastAPI application:

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at **`http://localhost:8000`** to access the interactive Three-Column Chat UI:
- **Column 1**: Conversational intake stream & contradiction alerts.
- **Column 2**: Structured State Inspector with field badges, change audit log, raw JSON, and direct manual override form.
- **Column 3**: Real-time Document Preview with legal disclaimers, completion badge, and copy button.

Interactive API Documentation (Swagger) is available at **`http://localhost:8000/docs`**.

---

## 🤖 LLM Provider Modes

### 1. Mock Mode (`LLM_PROVIDER=mock`) — Default & Offline
- Fully deterministic, offline rule-based extractor and response composer.
- Requires no API keys or internet connection.
- Ideal for automated regression tests, CI/CD pipelines, and local development.

### 2. Gemini Mode (`LLM_PROVIDER=gemini`) — Live Production AI
To use Google Gemini 2.5 Flash:
1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/).
2. Set in `.env`:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Restart the server. The application will automatically route extractions through Gemini with schema enforcement, grounding validation, and the 1-attempt repair flow.

---

## 🔌 API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health, environment, and LLM provider configuration status |
| `POST` | `/api/sessions` | Create a new intake session |
| `GET` | `/api/sessions/{id}` | Retrieve current session state, messages, changes, and document preview |
| `POST` | `/api/sessions/{id}/messages` | Send a user message and receive the assistant response turn |
| `PATCH` | `/api/sessions/{id}/state` | Directly override or modify a state field (bypassing LLM) |
| `GET` | `/api/sessions/{id}/document` | Retrieve rendered personal wishes document and completion status |
| `DELETE` | `/api/sessions/{id}` | Terminate and delete an active session |

---

## 📂 Repository Structure

```
WenupAI/
├── app/
│   ├── api/                  # FastAPI routers, schemas, and error handlers
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   └── errors.py
│   ├── docgen/               # Deterministic document rendering engine
│   │   └── renderer.py
│   ├── domain/               # Core domain models, state reducer, and planner
│   │   ├── models.py         # WishesState, FieldStatus, Change, Session
│   │   ├── reducer.py        # State reducer and atomic batch operations
│   │   ├── planner.py        # Deterministic interview planner
│   │   ├── contradictions.py # Contradiction detection engine
│   │   ├── rules.py          # Conditional cascade rules
│   │   └── validators.py     # Field validation logic
│   ├── llm/                  # LLM clients, schemas, prompts, and grounding
│   │   ├── base.py           # LLMClient abstract base class
│   │   ├── mock.py           # Offline deterministic MockLLMClient
│   │   ├── gemini.py         # Google Gemini 2.5 Flash client
│   │   ├── prompts.py        # Injection-safe system prompts
│   │   ├── schemas.py        # Pydantic extraction schemas
│   │   ├── grounding.py      # Token-overlap evidence grounding filter
│   │   ├── parsing.py        # JSON repair and robust response parser
│   │   └── composer.py       # Deterministic response composer with fallback
│   ├── services/             # Application services
│   │   ├── conversation.py   # Turn orchestration service
│   │   └── session_store.py  # In-memory session store with asyncio locks
│   ├── config.py             # Pydantic BaseSettings configuration
│   └── main.py               # FastAPI application entrypoint & static mounting
├── static/                   # Three-Column Vanilla Frontend UI
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/                    # Comprehensive Test Suite (98 tests)
│   ├── scenarios/            # Golden scenario test suite (8 scenarios)
│   │   └── test_golden_scenarios.py
│   ├── integration/          # API endpoints, manual corrections, static UI
│   │   ├── test_api_endpoints.py
│   │   ├── test_manual_correction.py
│   │   └── test_static_frontend.py
│   └── unit/                 # Unit tests for domain, LLM, grounding, docgen
├── AI_LOG.md                 # Complete chronological engineering log
├── DECISIONS.md              # Architectural decisions, trade-offs & roadmap
├── requirements.txt          # Production and testing dependencies
└── README.md                 # Project documentation
```

---

## 📜 License
This project is developed for the Wenup Engineering Technical Test.
