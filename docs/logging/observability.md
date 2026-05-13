# Observability

## Goal
Define the logging, tracing, and debug contracts required to observe document ingestion, extraction, chunking, graph construction, retrieval, and response generation end to end.

---

## Problem
Without strong observability, it is impossible to debug why a clause was missed, why a graph edge appeared, or why a response refused. Legal systems require traceability across all processing stages.

---

## Why It Matters
Observability is necessary for benchmarking, debugging, auditability, and hallucination control. Every critical system decision must be reconstructable from logs.

---

## Inputs
- Runtime events from all modules.
- Trace identifiers and processing versions.
- Confidence scores, thresholds, and validation events.
- Error and exception metadata.

---

## Outputs
- structured logs
- trace spans
- debug traces
- audit records
- failure dashboards

---

## Core Ideas
### Log Families
| Log Family | Required Content |
| --- | --- |
| Extraction logs | file type, strategy, page and region outcomes, failures |
| OCR logs | preprocessing, OCR engine, confidence, repair attempts |
| Parser QA logs | duplication removal, noise suppression, format validation, regression signals |
| Chunk logs | chosen strategy, boundaries, overlaps, degraded flags |
| Graph logs | node and edge counts, dedup actions, unresolved links |
| Retrieval logs | filters, mode scores, seeds, expansions, reranking |
| Response logs | support state, citation coverage, refusal reasons |
| Confidence logs | thresholds, score distributions, suppression events |
| Error logs | exceptions, stage failures, retry decisions, terminal status |

### Debug Trace Format
Each trace must be reconstructable as:

```text
trace_id
  -> document_id / query_id
  -> module
  -> stage
  -> input refs
  -> decision
  -> output refs
  -> confidence
  -> validation result
  -> error or warning
```

### Always-Logged Fields
- `trace_id`
- `document_id` or `query_id`
- `processing_version`
- `module`
- `stage`
- `timestamp`
- `status`
- `confidence_summary`
- `strategy_variant`

---

## Pipeline
1. Generate or propagate `trace_id` at upload or query entry.
2. Emit structured stage logs from every module.
3. Attach input and output artifact references to each stage log.
4. Emit warnings for low confidence, fallback use, or degraded artifacts.
5. Emit parser QA logs for duplicate-line cleanup, garbage suppression, and HTML or Markdown validation.
6. Emit terminal success, partial, or failure events.
7. Store logs in a queryable format for benchmark and debug workflows.

---

## Rules
### ALWAYS
- Log machine-readable events, not freeform strings only.
- Include threshold values when they influenced decisions.
- Preserve lineage across retries and reprocessing.
- Distinguish warnings from terminal failures.
- Log enough provenance to audit every answer.
- Log all extraction path variants separately: `simple_local`, `long_local`, `hybrid_region_precision`, `scan_recovery`.

### NEVER
- Log sensitive content without policy control.
- Drop low-confidence or fallback events.
- Collapse multiple processing versions into one undifferentiated log stream.
- Log only aggregated scores without source references.
- Lose the mapping from answer citations back to retrieval artifacts.

---

## Decision Logic
```text
if stage changes strategy or confidence state:
    emit decision log
if fallback or AI escalation occurs:
    emit warning log with reason code
if parser cleanup or output-format validation modifies retrieval-facing output:
    emit parser QA log
if validation fails:
    emit error log and terminal status or retry plan
if response is partial or refused:
    emit support-state log with trigger codes
```

Retention priority:
- highest: errors, refusals, unsupported claims, lineage changes
- high: extraction and retrieval decisions
- medium: normal successful stage summaries

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Same document reprocessed after parser change | Keep both processing versions and separate trace trees. |
| Partial pipeline success with failed graph step | Log successful upstream artifacts and blocked downstream dependencies. |
| Ambiguous citation resolution | Log candidate targets and suppression reason. |
| OCR repair rejected by validator | Log rejected output, validator reason, and fallback path. |
| User asks follow-up using prior context | Link new query trace to prior evidence trace references. |
| Very large bundle upload | Preserve per-document and bundle-level trace relationships. |

---

## Data Model
`LogEvent` fields:
- `event_id`
- `trace_id`
- `parent_event_id`
- `document_id`
- `query_id`
- `module`
- `stage`
- `status`
- `reason_codes[]`
- `input_refs[]`
- `output_refs[]`
- `confidence_summary`
- `thresholds`
- `error`
- `timestamp`

---

## Retrieval Impact
Retrieval observability makes ranking failures explainable. It also enables evidence-gap analysis and routing improvements by showing which retrieval modes succeeded or failed.

---

## GraphRAG Impact
Graph observability is required to explain why specific nodes were traversed, which edges were suppressed, and how graph expansion contributed to the final evidence set.

---

## Logging
Always log:
- one start and end event for every major stage
- all fallback activations
- all AI-assisted operations
- all parser QA and noise-suppression operations
- all validation failures
- all answer support states
- all unresolved citations and graph ambiguities

---

## Validation
- Validate that every trace is end-to-end connected.
- Validate required fields for every log family.
- Validate that critical errors are never sampled away.
- Validate log-to-artifact references.
- Periodically replay failures from logs to confirm reproducibility.

---

## Future Improvements
- Automated anomaly detection on confidence and fallback rates.
- Visual trace explorer for document and query lifecycles.
- Privacy-aware redaction policies by log field.
- Benchmark-linked failure clustering.
