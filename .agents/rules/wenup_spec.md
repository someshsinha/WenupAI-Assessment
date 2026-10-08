# Wenup Project Context & Core Rules

This project is the **Document Intake Assistant** for the **Wenup Engineering Technical Test**.

### Essential System Directives:
1. **Source of Truth**: Maintain structured state (JSON schema) explicitly. Conversation history is input to the LLM; structured state is the application's source of truth.
2. **Schema Fields**:
   - `full_name` (string)
   - `home_address` (string)
   - `covers_worldwide_assets` (boolean)
   - `has_children` (boolean)
   - `children_names` (array of strings, if has_children)
   - `executor` ({ name: string, relationship: string })
   - `specific_gifts` (array of { item: string, recipient: string })
   - `additional_wishes` (string)
3. **Core Principles**:
   - Resilient LLM handling: Validate JSON schemas strictly, support deterministic mocks / fixtures for offline evaluation.
   - Clean architecture: Separation of UI, Application Logic/State Manager, LLM Service, and Document Generator.
   - User correction support: State can be updated dynamically as user provides corrections.
   - Comprehensive test suite & AI log (`AI_LOG.md`).
