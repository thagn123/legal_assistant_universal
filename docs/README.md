# AI-Readable Architecture Documentation

## Purpose
This directory defines the architecture source of truth for the Adaptive Legal Multimodal GraphRAG Assistant.

The system is an evidence-grounded legal intelligence platform. It accepts legal documents from many jurisdictions, converts them into structured legal knowledge, builds graph relationships, retrieves cited evidence, and supports legal actions without inventing unsupported legal content.

## Read Order For AI Agents
1. `00-overview/project-vision.md`
2. `00-overview/repository-state.md`
3. `01-system-architecture/system-blueprint.md`
4. `01-system-architecture/layer-contracts.md`
5. `02-document-intelligence/adaptive-document-pipeline.md`
6. `02-document-intelligence/modality-routing.md`
7. `03-knowledge-graph/structured-legal-knowledge.md`
8. `04-retrieval-reasoning/hybrid-retrieval-and-graphrag.md`
9. `04-retrieval-reasoning/evidence-grounded-reasoning.md`
10. `05-actions/action-engine.md`
11. `06-quality/hallucination-safety-observability.md`
12. `07-implementation/implementation-roadmap.md`
13. `07-implementation/development-pipeline.md`
14. `07-implementation/ai-build-prompt.md`

## Documentation Roles
| Area | Role |
| --- | --- |
| `00-overview` | Defines project identity, scope, philosophy, and current repo status. |
| `01-system-architecture` | Defines the whole system and layer responsibilities. |
| `02-document-intelligence` | Defines ingestion, profiling, OCR, tables, images, and adaptive extraction. |
| `03-knowledge-graph` | Defines structured legal representation and graph semantics. |
| `04-retrieval-reasoning` | Defines hybrid retrieval, GraphRAG traversal, and evidence-grounded answers. |
| `05-actions` | Defines legal task execution such as drafting, risk analysis, and compliance checks. |
| `06-quality` | Defines hallucination prevention, validation, parser benchmarks, and observability. |
| `07-implementation` | Defines repo-aware implementation steps and a prompt for coding agents. |

## Existing Detailed References
The older module-level specs remain useful implementation references:
- `project-context.md`
- `architecture/system-overview.md`
- `parsing/*`
- `chunking/*`
- `graphrag/*`
- `retrieval/*`
- `validation/*`
- `logging/*`
- `prompts/*`
- `schemas/*`
- `ai/*`

When documents conflict, prefer this order:
1. Current code contracts in `src/schemas/*` and `src/config.py`
2. This numbered architecture handbook
3. Older module-level docs
4. Session logs such as `MULTILINGUAL_UPGRADE_LOG.md`
