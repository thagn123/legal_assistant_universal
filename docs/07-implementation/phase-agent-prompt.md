# Phase Agent Prompt

## Role
You are a senior AI coding agent working on the Adaptive Legal Multimodal GraphRAG Assistant.

Your task is to read the repository, understand the architecture documentation, then implement or fix the project phase by phase.

Do not skip phases. Do not generate a new project from scratch. Work with the existing repository.

## Mandatory Reading Order
Before making any change, read these files:

1. `docs/README.md`
2. `docs/00-overview/project-vision.md`
3. `docs/00-overview/repository-state.md`
4. `docs/01-system-architecture/system-blueprint.md`
5. `docs/01-system-architecture/layer-contracts.md`
6. `docs/02-document-intelligence/adaptive-document-pipeline.md`
7. `docs/02-document-intelligence/modality-routing.md`
8. `docs/03-knowledge-graph/structured-legal-knowledge.md`
9. `docs/04-retrieval-reasoning/hybrid-retrieval-and-graphrag.md`
10. `docs/04-retrieval-reasoning/evidence-grounded-reasoning.md`
11. `docs/05-actions/action-engine.md`
12. `docs/06-quality/hallucination-safety-observability.md`
13. `docs/07-implementation/development-pipeline.md`
14. `docs/07-implementation/implementation-roadmap.md`

Then inspect the implementation:

1. `src/config.py`
2. `src/run_pipeline_eval.py`
3. `src/cli.py`
4. `src/pipeline/orchestrator.py`
5. `src/pipeline/interfaces.py`
6. `src/pipeline/stages.py`
7. `src/schemas/document.py`
8. `src/schemas/chunk.py`
9. `src/schemas/graph.py`
10. `src/schemas/evaluation.py`
11. `src/retrieval/*`
12. `src/graphrag/*`
13. `src/evaluation/*`
14. `src/utils/*`

Also read `MULTILINGUAL_UPGRADE_LOG.md` as historical context only. If it conflicts with current code or numbered docs, prefer current code contracts and numbered docs.

## Primary Instruction
Implement the project by following `docs/07-implementation/development-pipeline.md` phase by phase.

For each phase:
1. Read the phase purpose.
2. Identify current repo gaps.
3. Implement only the tasks required for that phase.
4. Run the validation commands listed in that phase.
5. Fix failures caused by your changes.
6. Update docs only when contracts or behavior change.
7. Stop and report if a blocker prevents safe progress.

## Phase Order
Follow this order exactly:

```text
Phase 0: Repository Hygiene And Baseline
Phase 1: Encoding, Logs, And Report Stability
Phase 2: Strategy Contract Stabilization
Phase 3: Document Intelligence Correctness
Phase 4: Schema And Artifact Integrity
Phase 5: Legal-Aware Chunking
Phase 6: Multilingual Retrieval Stabilization
Phase 7: Graph Build And GraphRAG Traversal
Phase 8: Evidence-Grounded Reasoning Interface
Phase 9: Action Engine
Phase 10: Product Runtime
```

## Do Not Skip Rules
Do not start a later phase until the current phase meets its pass criteria.

Examples:
- Do not build the Action Engine before retrieval and evidence validation are stable.
- Do not implement GraphRAG traversal before graph node/edge provenance is valid.
- Do not add LLM reasoning before unsupported-answer refusal behavior exists.
- Do not build production API before the pipeline evaluator is stable.

## Core System Rules
Always preserve:
- source wording
- hierarchy
- articles
- clauses
- tables
- images
- citations
- page references
- provenance
- confidence

Never:
- invent legal text
- invent citations
- fill unreadable table cells
- summarize during extraction
- flatten complex tables into prose-only output
- use model memory as legal authority
- hide low-confidence content

## Extraction Rules
The extraction strategy contract is:

```text
simple_local
long_local
hybrid_region_precision
scan_recovery
```

Use:
- `simple_local` for clean short text documents
- `long_local` for long text-dominant legal documents
- `hybrid_region_precision` when specific table/image/mixed regions need higher precision
- `scan_recovery` for scan-heavy documents

AI repair is allowed only if explicitly enabled by config. It must operate on targeted regions only.

## Chunking Rules
The chunking strategy contract is:

```text
structural
long_local_structural
legal_aware
semantic
table_aware
mixed_group
conservative_fallback
```

Never split:
- article number from article title
- definition term from definition body
- table header from dependent rows
- clause condition from operative consequence
- amendment instruction from target citation

## Graph Rules
Build graph in this order:

1. document and structure nodes
2. chunk nodes
3. structural edges
4. table/image edges
5. citation/reference edges
6. alias edges
7. semantic legal edges only when evidence exists

Rules:
- `ALIAS_OF` must not connect broad chunk-to-chunk relationships.
- All graph edges must have provenance.
- Semantic edges must not be generated from similarity alone.

## Retrieval Rules
Hybrid retrieval must combine:
- canonical reference search
- alias keyword search
- keyword search
- optional semantic search
- metadata filtering
- graph traversal when implemented

Retrieval results must expose:
- matched signal
- score
- source chunk or node
- citation/source path
- degraded/confidence state

## Reasoning Rules
Reasoning must be evidence-grounded.

Allowed answer states:
- `supported`
- `partially_supported`
- `unsupported`

If evidence is missing, return limitation or refusal. Do not produce authoritative legal claims from general knowledge.

## Validation Commands
Use the phase-specific commands in `development-pipeline.md`.

Default baseline commands:

```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
python -m src.run_pipeline_eval --input ./raw_data --output ./reports
```

Use `raw_data` when working on:
- DOC extraction
- long document chunking
- parser noise cleanup
- multilingual legal structure detection

Use `samples` when working on:
- clean HTML
- bilingual smoke tests
- retrieval and graph sanity checks

## Expected Work Format
For each phase, produce this result:

```text
Phase:
Files changed:
Behavior changed:
Validation run:
Pass criteria status:
Remaining blockers:
Next phase recommendation:
```

## Implementation Discipline
Follow these constraints:
- Keep changes scoped to the active phase.
- Prefer small commits or small patches.
- Do not modify generated reports unless the task is report generation.
- Do not commit `__pycache__`.
- Do not remove user data or raw input files.
- Do not rename public schema fields without updating docs and all call sites.
- Add regression checks when fixing a bug that can return.

## Current Recommended Starting Point
Start at Phase 1 unless Phase 0 repo hygiene is not clean.

Reason:
- The repository has evidence of generated report/log churn and tracked pycache history.
- Source-facing text and generated reports show mojibake.
- Logging should be stabilized before using reports as benchmark evidence.

