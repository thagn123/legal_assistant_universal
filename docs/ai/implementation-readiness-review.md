# Implementation Readiness Review (AI-Readable)

## Goal
Provide an AI-consumable assessment of the current repository state (`src/` + `docs/`) to guide safe implementation, refactoring, and completion of a Legal Multimodal GraphRAG system.

---

## Problem
The repo contains a large, multi-stage local-first pipeline implementation plus an extensive specification set. The risk is mismatch between spec and code, ambiguous enums, and observability issues that degrade evaluation and debugging.

---

## Why It Matters
Downstream AI agents must understand what exists, what is incomplete, and what is unsafe to change. This review is a guardrail to prevent regressions, hallucination-prone behaviors, and spec drift.

---

## Inputs
- `docs/` specification set (project context, parsing, chunking, GraphRAG, retrieval, validation, logging, prompts, schema).
- `src/` Python implementation:
  - `src/pipeline/orchestrator.py`
  - `src/pipeline/interfaces.py`
  - `src/pipeline/stages.py`
  - `src/schemas/*`
  - `src/retrieval/*`
  - `src/graphrag/*`
  - `src/evaluation/*`
  - `src/utils/*`
  - `src/config.py`
  - `src/cli.py` and `src/run_pipeline_eval.py`

---

## Outputs
- Status of the repository by subsystem.
- Highest-risk issues that affect correctness and trust.
- Specific refactor and validation recommendations.
- Action priority list for AI implementation agents.

---

## Core Ideas
### System Shape (What Exists)
- A local-first, multi-stage pipeline orchestrator runs: profiling → extraction → structuring → cleaning/validation → chunking → graph building → retrieval smoke test.
- Canonical schema exists in `src/schemas/document.py` and broadly matches `docs/schemas/document-schema.md`.
- Retrieval engine supports multilingual keyword + alias + canonical reference matching, with optional embedding backend.
- Observability is implemented via `src/utils/logging.py` as JSONL-like event capture plus console logs.

### System Shape (What Is Missing / Incomplete)
- The pipeline is primarily an evaluation runner, not a production service (no HTTP API, storage layer, async orchestration).
- AI-assisted extraction/repair is gated by config but does not define provider integration; strict accuracy mode exists conceptually but should be verified end-to-end.
- GraphRAG traversal policy exists in docs; code likely builds graphs and has a retrieval smoke test, but full traversal-and-expansion integration may be incomplete.

---

## Pipeline
1. Use `src/run_pipeline_eval.py` to run evaluation over `samples/`.
2. `PipelineOrchestrator` executes pipeline stages and accumulates `DocumentEvalResult`.
3. Stages emit structured logs; artifacts and reports are written under `reports/`.
4. Retrieval smoke tests provide sanity checks, not full user-facing QA.

---

## Rules
### ALWAYS
- Keep `docs/` as the source of truth for architecture and constraints.
- Keep extraction local-first; use AI only for table/image/scan repair under strict no-invention constraints.
- Preserve canonical schema invariants: provenance, confidence, hierarchy, table and image first-class objects.
- Require deterministic validation and explicit degraded flags for low-confidence content.
- Maintain reproducible logs: every decision must be observable and tied to thresholds.

### NEVER
- Change canonical schema semantics without updating both `docs/schemas/document-schema.md` and `src/schemas/*`.
- Introduce AI generation that can add missing text or "fix" content by guessing.
- Treat graph adjacency as legal proof; graph is a retrieval aid unless backed by anchored evidence.
- Hide parsing failures by silently skipping pages/regions.

---

## Decision Logic
Severity classification for issues:
```text
if issue can cause invented text, broken citations, or wrong legal meaning:
    severity = P0 (blocker)
elif issue makes logs/metrics unreliable or hides failures:
    severity = P1 (high)
elif issue is maintainability or performance only:
    severity = P2 (medium)
else:
    severity = P3 (low)
```

---

## Edge Cases
| Case | Risk | Required Handling |
| --- | --- | --- |
| Mixed encodings / mojibake in strings | Parser output and logs contain garbage characters | Enforce UTF-8, fix string literals, avoid broken escapes, test report rendering. |
| Long text documents with sparse tables/images | Wrong escalation strategy can increase cost or distort structure | Keep body in `long_local`, escalate only detected table/image regions. |
| Borderless tables | Deterministic table parser may fail | Use AI repair only for topology reconstruction, never for content invention. |
| OCR low confidence | Unreliable authority | Mark degraded, restrict authoritative answering, preserve raw OCR vs cleaned text. |

---

## Data Model
Key enums and fields that must remain consistent across code and docs:
- `DocumentProfile.extraction_strategy`: `simple_local | long_local | hybrid_region_precision | scan_recovery`
- Config flags:
  - `enable_ai_repair`
  - `strict_accuracy_mode`
  - `parser_noise_cleanup`
- Confidence gates:
  - `ocr_confidence_threshold`
  - `table_topology_threshold`
  - `chunk_authority_threshold`
- Traceability must include `trace_id`, `source_hash`, and `processing_version`.

---

## Retrieval Impact
Major positive:
- Canonical reference matching + alias expansion improves exact clause retrieval and multilingual queries.

Major risks:
- If chunk boundaries drift or contain parser noise, retrieval will return irrelevant or duplicated content.
- If logs do not separate status vs severity, failure analysis becomes unreliable.

---

## GraphRAG Impact
Major positive:
- Schema supports structure nodes and evidence objects as first-class graph material.

Major risks:
- Graph expansion must remain conservative and provenance-bound, otherwise it amplifies noise.

---

## Logging
P0: Logging schema bug risk to confirm and fix:
- Ensure log `status` (pass/fail/warning) is not conflated with log severity (info/warning/error).
- Ensure stage end events encode both: stage outcome and severity.

---

## Validation
Minimum validation suite to implement and keep green:
- Stage-level: non-empty pages, order monotonicity, provenance present on blocks/tables/images.
- Noise: duplicated line rate and footer/header leakage checks when `parser_noise_cleanup=True`.
- Chunk: prohibited-split checks (definitions, table headers, clause numbering).
- Graph: schema validation + provenance completeness + unresolved citation handling.
- Retrieval: smoke tests for exact article lookup and cross-language alias retrieval.

---

## Future Improvements
- Split `src/pipeline/stages.py` into smaller modules per stage for testability.
- Formalize JSON schema for logs and canonical objects.
- Add explicit graph traversal integration for GraphRAG (beyond smoke test).
- Add production service layer (API + storage + job orchestration) once core quality is stable.

