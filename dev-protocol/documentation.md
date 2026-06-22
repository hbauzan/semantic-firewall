# DOCUMENTATION SYNCHRONIZATION WORKFLOW

For every logical change, database modification, API adjustment, or UI restructure, you must synchronously update the following documentation assets. These documents serve as the definitive "recovery core" of the codebase.

| File | Core Purpose & Action Required |
| :--- | :--- |
| **`manifest.json`** | **State, Stage, and Historical Audit Trail:**<br>Must serve as the chronological ledger of the system. Declare the active stage, versioning timeline, and (where applicable) entrypoints/API endpoints, ports, service mappings, feature flags, and the LLM provider/model configuration in use (provider, model id, local-vs-remote). This file must allow any external AI to immediately understand the project's historical progression, past iterations, and exact current state. |
| **`architecture_spec.md`** | **Low-Level Design (LLD) & Technical Rules:**<br>Document data schemas, data flows, and security/scalability policies. For LLM apps, also document the **provider interface contract** (inputs/outputs, error modes), the local-vs-remote adapter boundary, prompt/templating contracts, and token/latency/cost expectations. When combined with `CONTEXT.md` (and `CONTEXT.blueprint.md` if available), it must contain the comprehensive technical specifications required to rebuild the entire codebase from absolute zero without losing functional integrity. |
| **`README.md`** | **First-Time Operational Onboarding Guide:**<br>Must act as a practical, step-by-step operational setup guide for a developer or team member running the tool on their local machine for the very first time. It must detail environmental prerequisites, initialization commands, verification testing, and basic execution steps. Keep this updated to ensure zero setup friction. |

---

## CONTEXT & BLUEPRINT WORKFLOW

By default, the codebase domain context is managed in a glossary format to ensure clean domain definitions. However, a specialized blueprint mode exists for tracking codebase layout.

### 1. CONTEXT.md (Standard Run - Default)
Behaves strictly as a **Domain Model Glossary & Ubiquitous Language** reference, devoid of code or implementation details.

- **Structure**: Define terms precisely under subheadings. Keep definitions tight (1-2 sentences max defining what a concept *is*, not what it *does*).
- **Aliases**: Be opinionated. If multiple words exist for the same concept, pick the canonical term and list the others under an `_Avoid_` section.
- **Relationships**: Show bold term names and express cardinality/relationships between concepts.
- **Context Mapping**: For repositories with multiple subdomains or modules, a `CONTEXT-MAP.md` at the root must map out each context (e.g. `[Ordering](./src/ordering/CONTEXT.md)`) and their relationships.
- **Update Frequency**: Update terms inline as decisions are made; do not batch glossary updates.

### 2. CONTEXT.blueprint.md (Bootstrap Run)
The **Bootstrap Run** is a specialized mode containing a comprehensive codebase re-generation blueprint.

- **Activation**: Activated in one of two ways:
  1. Setting `"bootstrap_run": true` in `manifest.json`.
  2. Explicit declaration by the user in the prompt.
- **Output File**: Write/update the blueprint in a separate file: **`CONTEXT.blueprint.md`**.
- **Content Requirements**:
  - File-by-file inventory and mapping.
  - Complete structural dependencies between modules.
  - Technical debt analysis and context anchors.
  - Absolute context density to enable repository regeneration from zero.
