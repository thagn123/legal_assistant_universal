# Repository State

## Goal
Summarize the current implementation so AI agents can continue from the real repo instead of rebuilding from scratch.

## Current Codebase Shape
The repo already contains a Python pipeline evaluator under `src/`.

Primary entrypoints:
- `src/run_pipeline_eval.py`
- `src/cli.py`
- `src/config.py`

Primary runtime modules:
- `src/pipeline/orchestrator.py`
- `src/pipeline/interfaces.py`
- `src/pipeline/stages.py`
- `src/schemas/*`
- `src/retrieval/*`
- `src/graphrag/*`
- `src/evaluation/*`
- `src/utils/*`

## Implemented Capabilities
| Capability | Current Status |
| --- | --- |
| CLI evaluation runner | Implemented. |
| File discovery | Implemented for PDF, DOCX, DOC, HTML, and images. |
| Local-first pipeline stages | Implemented in orchestrator and stages. |
| Canonical schemas | Implemented in `src/schemas/*`. |
| Multilingual retrieval metadata | Implemented with `language`, `canonical_refs`, and `hierarchy_path`. |
| Cross-language query normalization | Implemented in `src/retrieval/*`. |
| Graph alias enrichment | Implemented in `src/graphrag/legal_ontology.py`. |
| Evaluation reports | Implemented in JSON and Markdown. |
| Structured logging | Implemented, but schema should be reviewed. |

## Important Recent Upgrade
`MULTILINGUAL_UPGRADE_LOG.md` documents a multilingual upgrade:
- language detection with confidence and jurisdiction hints
- legal alias mapping between Vietnamese and English terms
- canonical reference IDs such as `article_1`
- retrieval passes using canonical refs, aliases, keywords, and optional semantic search
- `ALIAS_OF` graph edges for cross-language equivalents
- multilingual metrics in reports

## Current Risks
| Risk | Impact | Priority |
| --- | --- | --- |
| Mojibake in comments, logs, and Markdown output | Pollutes reports and may confuse AI/regex processing. | High |
| `long_local` vs `long_local_structural` naming split | Can confuse implementation and metrics. | High |
| `src/pipeline/stages.py` is large and owns many responsibilities | Harder to test and maintain. | Medium |
| Reports and pycache are present in git history | Repo hygiene issue; does not affect runtime directly. | Medium |
| AI-assisted repair is gated but provider integration is not production-ready | Strict mode is conceptual unless wired and tested. | Medium |

## Required Next Actions
1. Normalize UTF-8 text in source comments, report strings, and `MULTILINGUAL_UPGRADE_LOG.md`.
2. Standardize strategy naming:
   - extraction strategy: `simple_local`, `long_local`, `hybrid_region_precision`, `scan_recovery`
   - chunking strategy: `structural`, `long_local_structural`, `table_aware`, `mixed_group`, `conservative_fallback`
3. Add regression checks for:
   - no chunk-to-chunk `ALIAS_OF`
   - no invented text
   - no empty chunks
   - canonical refs present for structured legal chunks
4. Split `src/pipeline/stages.py` after correctness is stable.

