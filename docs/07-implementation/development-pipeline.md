# Development Pipeline

## Goal
Define the step-by-step build and fix pipeline for this project so implementation agents can progress safely from the current repo state to a complete Adaptive Legal Multimodal GraphRAG Assistant.

This is the execution roadmap. Follow it in order. Do not build later product features before earlier correctness gates are stable.

## Operating Rule
Every phase must produce:
- working code
- validation output
- known limitations
- regression checks or benchmark signals
- updated docs when contracts change

Do not move to the next phase when the current phase has unresolved blocker issues.

## Phase 0: Repository Hygiene And Baseline

### Purpose
Make the repo clean enough that future changes can be reviewed and debugged reliably.

### Build / Fix Tasks
- Remove tracked `__pycache__` and generated report/log artifacts from future commits.
- Keep `.gitignore` aligned with Python and pipeline outputs.
- Decide whether `reports/` is test artifact storage or generated runtime output.
- Record current baseline results from `samples/` and `raw_data/`.
- Identify all dirty files before making new feature changes.

### Validation
```bash
git status --short
python -m src.run_pipeline_eval --input ./samples --output ./reports
```

### Pass Criteria
- Git status shows only intended source/doc changes before each commit.
- Baseline sample run completes.
- Generated reports are not accidentally mixed with source changes.

### Blockers
- Dirty generated files hide source changes.
- Pycache files are tracked or repeatedly modified.

## Phase 1: Encoding, Logs, And Report Stability

### Purpose
Remove mojibake and make logs/reports trustworthy before deeper feature work.

### Build / Fix Tasks
- Normalize UTF-8 strings in source comments, docstrings, report labels, and `MULTILINGUAL_UPGRADE_LOG.md`.
- Replace broken symbols in CLI/report output with ASCII or valid UTF-8.
- Fix logging schema so `severity` and `stage_status` are separate concepts.
- Ensure JSONL logs include `trace_id`, `document_id`, `stage`, `status`, `severity`, and `timestamp`.
- Add parser QA log events for noise cleanup and AI escalation decisions.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports --log-level DEBUG
```

Check:
- Markdown reports render clean text.
- JSON reports serialize without broken characters.
- Log events are queryable by stage status and severity separately.

### Pass Criteria
- No visible mojibake in reports, README, or source-facing output.
- Stage outcomes remain machine-readable.
- Log schema matches `docs/logging/observability.md`.

### Blockers
- Broken characters appear in generated reports.
- Log `status` still mixes `info/warning/error` with `pass/warning/fail`.

## Phase 2: Strategy Contract Stabilization

### Purpose
Make extraction and chunking strategy names deterministic across docs, schemas, logs, metrics, and code.

### Build / Fix Tasks
- Keep extraction strategies limited to:
  - `simple_local`
  - `long_local`
  - `hybrid_region_precision`
  - `scan_recovery`
- Keep chunking strategies limited to:
  - `structural`
  - `long_local_structural`
  - `legal_aware`
  - `semantic`
  - `table_aware`
  - `mixed_group`
  - `conservative_fallback`
- Add constants or enums in code rather than repeated string literals.
- Ensure reports show both extraction strategy and chunking strategy.
- Update docs whenever a strategy is added or renamed.

### Validation
```bash
rg -n "simple_local|long_local|hybrid_region_precision|scan_recovery|long_local_structural" src docs
python -m src.run_pipeline_eval --input ./samples --output ./reports
```

### Pass Criteria
- No ambiguous strategy naming.
- Extraction and chunking strategies are not conflated.
- Metrics and reports use the same vocabulary as docs.

### Blockers
- Same strategy name used for different meanings.
- Reports omit chunking strategy or extraction strategy.

## Phase 3: Document Intelligence Correctness

### Purpose
Make extraction reliable across simple text, long legal text, DOC/DOCX, HTML, PDF, scans, tables, and images.

### Build / Fix Tasks
- Split document profiling logic from extraction logic.
- Preserve raw extraction and cleaned extraction separately.
- Improve `.doc` handling and clearly mark table topology degradation.
- Ensure long text documents use `long_local` for the main body.
- Route sparse tables/images inside long docs as region-level overrides.
- Strengthen parser noise cleanup without deleting legally meaningful repeated text.
- Add explicit degraded status for low-confidence OCR/table/image outputs.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
python -m src.run_pipeline_eval --input ./raw_data --output ./reports
```

Check:
- blocks extracted
- pages extracted
- sections/articles detected
- tables/images counted
- warnings are meaningful

### Pass Criteria
- Clean HTML/DOCX samples produce structured blocks and chunks.
- Long DOC/DOCX legal files produce article-level or clause-level chunks.
- Table topology loss is marked degraded instead of hidden.
- Parser noise warnings are visible but not destructive.

### Blockers
- Valid files produce zero blocks.
- Long legal documents become one huge chunk.
- Table content is silently flattened without warning.

## Phase 4: Schema And Artifact Integrity

### Purpose
Ensure every pipeline output can be trusted by downstream chunking, graph, retrieval, and reasoning.

### Build / Fix Tasks
- Validate canonical document object integrity.
- Ensure every block/table/image has provenance and confidence.
- Add referential integrity checks for sections, articles, clauses, blocks, chunks, and graph nodes.
- Ensure raw vs clean text fields are populated consistently.
- Add schema tests for Pydantic and fallback `BaseModel` behavior.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
```

Add or run checks for:
- orphan block refs
- missing page refs
- missing confidence
- missing traceability
- invalid graph node or edge types

### Pass Criteria
- Canonical document can be serialized to JSON.
- No evidence-bearing object lacks source anchors.
- Fallback model behavior does not break report generation.

### Blockers
- Missing provenance on chunks or graph edges.
- Schema fallback creates objects that differ materially from Pydantic behavior.

## Phase 5: Legal-Aware Chunking

### Purpose
Optimize chunking for retrieval without breaking legal meaning.

### Build / Fix Tasks
- Enforce prohibited split rules:
  - article number from title
  - definition term from definition body
  - table header from dependent rows
  - condition from operative consequence
- Add chunk validation checks.
- Add table sibling chunks and image evidence chunks where needed.
- Add parent hierarchy carryover for long documents.
- Add multilingual fields: `language`, `canonical_refs`, `hierarchy_path`.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
python -m src.run_pipeline_eval --input ./raw_data --output ./reports
```

### Pass Criteria
- No empty chunks.
- No one-chunk output for long structured legal documents.
- Chunks preserve hierarchy and citations.
- Structured chunks contain canonical refs where possible.

### Blockers
- Chunking uses fixed-size splitting as the primary strategy.
- Chunks lose article/clause numbering.

## Phase 6: Multilingual Retrieval Stabilization

### Purpose
Make Vietnamese/English retrieval reliable through canonical references, aliases, keywords, and optional semantic search.

### Build / Fix Tasks
- Verify `language_detector.py` language and confidence behavior.
- Verify `query_normalizer.py` maps Article/Art/Dieu patterns to canonical refs.
- Verify `legal_aliases.py` covers core legal structure terms.
- Verify `canonical_references.py` generates stable refs for sections/articles/clauses.
- Tune retrieval scoring with term frequency and length penalty.
- Add tests for cross-language queries.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
```

Smoke tests:
- English query finds Vietnamese article by canonical ref.
- Vietnamese query finds English article by alias/canonical ref.
- Long chunks do not rank above exact short hits due to length alone.

### Pass Criteria
- Cross-language hit rate is meaningful, not inflated by broad matches.
- Retrieval debug logs show which signal matched.
- Exact article lookup outranks weak keyword matches.

### Blockers
- Retrieval returns results without explaining match signals.
- Cross-language hit rate is 100% because queries are too broad or false-positive.

## Phase 7: Graph Build And GraphRAG Traversal

### Purpose
Turn structured documents and chunks into a useful legal graph and use it for retrieval expansion.

### Build / Fix Tasks
- Ensure graph nodes map to document, section, article, clause, table, image, chunk, citation, and legal concept objects.
- Build structural edges first.
- Add citation and reference edges when evidence exists.
- Add semantic edges only with explicit evidence.
- Prevent chunk-to-chunk `ALIAS_OF` edges.
- Implement traversal policy with depth, confidence, and edge-type limits.
- Assemble graph-expanded evidence bundles for reasoning.

### Validation
```bash
python -m src.run_pipeline_eval --input ./samples --output ./reports
```

Check:
- graph node counts
- structural edge counts
- `ALIAS_OF` edge counts
- low-confidence edge counts
- traversal result paths

### Pass Criteria
- Graph has structure edges for structured documents.
- `ALIAS_OF` is limited to compatible non-chunk nodes.
- Traversal expands useful context without graph explosion.

### Blockers
- Graph edges lack provenance.
- `ALIAS_OF` connects chunks broadly.
- Graph traversal pulls unrelated nodes.

## Phase 8: Evidence-Grounded Reasoning Interface

### Purpose
Add a reasoning layer that can answer, refuse, or limit output based on retrieved evidence.

### Build / Fix Tasks
- Define query intent classification.
- Define evidence bundle schema.
- Implement support-state validation:
  - `supported`
  - `partially_supported`
  - `unsupported`
- Generate answers only from retrieved evidence.
- Require citations for material claims.
- Add refusal/limitation behavior for missing evidence.

### Validation
Use deterministic fixtures before adding LLM calls:
- direct clause lookup
- missing clause query
- conflicting evidence query
- low-confidence OCR query

### Pass Criteria
- Unsupported questions do not produce authoritative answers.
- Every material claim maps to evidence.
- Source quotes are distinguishable from generated explanation.

### Blockers
- Reasoning uses model memory as authority.
- Answers contain uncited legal claims.

## Phase 9: Action Engine

### Purpose
Support legal workflows beyond Q&A.

### Build / Fix Tasks
- Implement action request schema.
- Add action types:
  - contract drafting
  - compliance checking
  - risk analysis
  - clause recommendation
  - cross-document comparison
- Validate evidence support before action output.
- Mark generated language separately from source language.
- Add workflow-specific reports.

### Validation
Test with uploaded evidence only:
- draft an employment contract clause from uploaded labor law
- check a policy against uploaded regulation
- detect risky or missing clauses in a sample contract

### Pass Criteria
- Drafts cite source basis and assumptions.
- Risk findings cite exact source evidence.
- Compliance checks expose missing evidence.

### Blockers
- Generated clauses presented as source text.
- Compliance claims made without uploaded authority.

## Phase 10: Product Runtime

### Purpose
Move from evaluation pipeline to usable application infrastructure.

### Build / Fix Tasks
- Add API service for uploads, jobs, documents, queries, and actions.
- Add async job orchestration.
- Add persistent storage for files, canonical docs, chunks, graph, indexes, logs, and reports.
- Add authentication, authorization, tenant isolation, and audit trails.
- Add UI or API client for document spaces and query sessions.
- Add deployment configuration.

### Validation
- upload document
- process document asynchronously
- inspect parse report
- query document space
- view citations and evidence
- run action workflow

### Pass Criteria
- Jobs are resumable and auditable.
- Users can query only their own document spaces.
- Every answer links back to stored evidence.

### Blockers
- No persistent artifact versioning.
- No access-control model.
- No audit trail for generated legal output.

## Recommended Build Order
```text
0 repo hygiene
1 encoding/log/report stability
2 strategy contracts
3 document intelligence correctness
4 schema integrity
5 legal-aware chunking
6 multilingual retrieval
7 graph build + GraphRAG traversal
8 evidence-grounded reasoning
9 action engine
10 production runtime
```

## Current Best Next Step
Start with Phase 1.

Reason:
- Current repo shows mojibake in source-facing text and reports.
- Logs need stronger separation between severity and stage status.
- Fixing this first makes every later benchmark and report more trustworthy.

