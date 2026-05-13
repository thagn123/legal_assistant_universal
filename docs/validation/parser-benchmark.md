# Parser Benchmark

## Goal
Define how to evaluate document parsing, structure preservation, chunk quality, retrieval quality, and graph quality for the legal multimodal GraphRAG system.

---

## Problem
Without a benchmark, parser improvements are subjective and regressions go unnoticed. Legal document quality cannot be measured by text extraction accuracy alone.

---

## Why It Matters
The benchmark establishes whether the system preserves evidence well enough for retrieval and grounded legal reasoning. It also guides routing thresholds and failure handling policies.

---

## Inputs
- Gold-standard annotated document set.
- Predicted extraction, chunk, retrieval, and graph artifacts.
- Failure logs and manual review notes.
- Query evaluation sets by task class.

---

## Outputs
- benchmark scorecards
- per-stage metrics
- failure taxonomy
- manual review decisions
- regression alerts

---

## Core Ideas
### What to Measure
| Area | Measures |
| --- | --- |
| Extraction accuracy | character or token accuracy, omission rate, insertion rate |
| OCR quality | CER, WER, line grouping stability, unreadable region rate |
| Structure preservation | hierarchy detection F1, numbering fidelity, order fidelity |
| Table fidelity | topology accuracy, merged-cell preservation, row and header correctness |
| Parser noise control | duplicated-line rate, footer or header leakage rate, garbage-fragment rate |
| Chunk quality | boundary correctness, context preservation, retrieval hit rate |
| Retrieval quality | precision, recall, MRR, nDCG, citation-hit rate |
| Graph quality | node precision, edge precision, provenance completeness, unresolved ambiguity rate |

### Benchmark Composition
The gold set must include:
- plain text statutes
- long contracts
- long plain-text laws with sparse embedded tables
- scanned PDFs
- table-heavy schedules
- mixed-layout forms
- multilingual documents
- image-bearing annexes

### Failure Taxonomy
- text omission
- text invention
- structure flattening
- broken reading order
- table distortion
- OCR corruption
- wrong citation resolution
- noisy graph edge
- unsupported answer support gap

---

## Pipeline
1. Build or update the annotated benchmark corpus.
2. Run the full pipeline on benchmark documents.
3. Compare extraction outputs to gold annotations.
4. Run parser QA checks for duplication, parser trash, broken ordering, and output-format fidelity in HTML and Markdown.
5. Evaluate chunk boundaries and retrieval hits on labeled queries.
6. Evaluate graph nodes, edges, and provenance completeness.
7. Aggregate metrics by document family and jurisdiction class.
8. Review critical failures manually.
9. Publish scorecards and regression reports.

---

## Rules
### ALWAYS
- Evaluate structure and provenance, not only text similarity.
- Separate metrics by document family.
- Keep gold annotations versioned.
- Log failure examples with source anchors.
- Use manual review for ambiguous legal structures and severe failures.
- Benchmark `local`, `long_local`, and `hybrid_region_precision` extraction paths separately.

### NEVER
- Average away critical failure classes such as invented text.
- Treat benchmark improvements on one document family as global improvement.
- Score low-confidence degraded outputs as fully authoritative.
- Change metric definitions midstream without versioning.
- Ignore unresolved edge cases in the benchmark report.
- Ignore parser-trash regressions just because semantic retrieval still appears acceptable.

---

## Decision Logic
```text
if extraction invents content:
    mark critical failure
elif hierarchy preservation falls below threshold:
    block release for legal retrieval use
elif parser_noise_control falls below threshold:
    block release for retrieval-facing outputs
elif retrieval citation-hit rate drops materially:
    investigate chunking and indexing regressions
elif graph provenance completeness drops:
    block graph-dependent features
else:
    allow release with tracked warnings
```

Manual review triggers:
- critical failure classes
- new document families
- low-confidence benchmark anomalies
- disagreement between automated scores and user-visible quality

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Gold annotation itself is ambiguous | Record ambiguity class and allow multi-answer evaluation where justified. |
| Multiple valid chunk boundaries | Score against acceptable boundary sets, not one rigid split only. |
| Borderless tables with alternate valid topologies | Use graded topology equivalence, not strict identical geometry only. |
| External citation target missing from corpus | Score citation parsing separately from internal resolution. |
| Mixed-language clause alignment | Evaluate both language preservation and alignment linkage. |
| Updated parser changes normalization only | Compare raw extraction fidelity separately from normalized output fidelity. |

---

## Data Model
`BenchmarkRecord` fields:
- `benchmark_id`
- `document_id`
- `document_family`
- `gold_artifact_refs`
- `predicted_artifact_refs`
- `metrics`
- `critical_failures[]`
- `review_status`
- `path_variant` 

---

## Retrieval Impact
The benchmark reveals whether parsing and chunking changes improve or degrade retrieval for legal tasks. Retrieval metrics must be interpreted together with extraction and structure metrics.

---

## GraphRAG Impact
Graph quality metrics determine whether graph expansion can be trusted. Low provenance completeness or noisy edge precision should automatically restrict GraphRAG usage.

---

## Logging
Always log:
- benchmark version
- metric definitions
- per-document scores
- failure samples
- manual review outcomes
- release gating decisions
- parser QA results for `html` and `markdown` outputs

---

## Validation
- Validate metric computation reproducibility.
- Validate benchmark corpus coverage across document families.
- Validate release gates on critical failure classes.
- Periodically audit manual review consistency.
- Compare benchmark results with real-world failure logs.

---

## Future Improvements
- Active-learning benchmark expansion from production failures.
- Better scoring for diagram and image evidence extraction.
- Jurisdiction-specific legal structure benchmarks.
- Time-based trend analysis for pipeline regressions.
