# Wenup Engineering Test — Document Intake Assistant Specification

## Project Overview
Build the **Document Intake Assistant**, a web application that conducts a conversational interview to collect structured personal wishes, maintains an explicit structured state schema as the single source of truth, and produces a live draft **Personal Wishes Document** with clear disclaimers (fictional, not legal advice).

---

## Key Requirements & Capabilities

### 1. Information to Collect (Structured State Schema)
- `full_name`: string (User's full legal name)
- `home_address`: string (Residential address)
- `covers_worldwide_assets`: boolean (Whether the document covers assets worldwide)
- `has_children`: boolean (Whether the user has children)
- `children_names`: list of strings (Names of children, required if `has_children` is true)
- `executor`: object
  - `name`: string (Full name of appointed executor)
  - `relationship`: string (Relationship to the user, e.g., brother, friend, spouse)
- `specific_gifts`: list of objects / text (Specific gifts/items bequeathed to beneficiaries)
- `additional_wishes`: string (Any funeral wishes, special messages, or remaining instructions)
- `metadata` / `completion_status`: tracking of confirmed vs unconfirmed fields

### 2. Conversational & LLM Behavior
- **Multi-turn conversation**: Conduct dynamic, friendly, professional intake interview.
- **Ambiguity & Missing Information**: Ask sensible follow-up questions when input is missing, ambiguous, or contradictory.
- **Batch Information Intake**: Handle inputs that provide multiple fields at once in any reasonable order (e.g., *"My name is Jane Doe living at 12 High St, London. I want my brother James to be executor"*).
- **Corrections**: Seamlessly allow the user to correct previously supplied information at any point in the chat.
- **No Hallucinations / Explicit Unknowns**: Never invent facts; leave unconfirmed values explicitly unassigned or flagged.
- **No Redundant Questions**: Do not ask for information that has already been validated and captured.

### 3. Architecture & Separation of Concerns
- **UI / Frontend**: Clean, modern interface with 3 interactive sections:
  1. Interactive Multi-turn Chat Assistant
  2. Live Structured State Inspector (visual schema view & raw JSON preview with field status indicators)
  3. Live Draft Document Preview (formatted Personal Wishes Document with real-time updates and export/copy capability)
- **Application Logic & State Manager**: State machine / schema validator ensuring valid transitions and deterministic merges.
- **LLM Layer & Providers**:
  - Pluggable LLM interface (e.g. OpenAI / Anthropic / Google Gemini / Ollama).
  - Deterministic Mock / Offline Fallback Provider for instant local running and reproducible test fixtures (covering valid, ambiguous, and malformed responses).
  - Robust output parsing, JSON schema validation, error recovery, and retries.
- **Document Generator**: Deterministic template/renderer turning confirmed structured state into a clean draft document clearly labeled with legal disclaimers.

### 4. Robustness, Testing & Submission Deliverables
- **Automated Tests**: Unit and integration tests for state extraction, validation, correction handling, mock fixtures, and document rendering.
- **AI Log (`AI_LOG.md`)**: Log of prompt engineering, iterations, corrections, and architectural decisions.
- **Configuration & Security**: Environment configuration (`.env.example`), secrets kept out of version control.
- **Production Notes**: Clear notes on scalability, security, telemetry, and human-in-the-loop workflows.
