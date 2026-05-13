# Chunking Decision Tree

## Goal
Define deterministic routing logic for choosing the correct chunking strategy for each legal document or document region set.

---

## Problem
Different legal documents need different chunking behavior. Using one universal strategy either over-splits structured laws or under-preserves complex tables, scans, and mixed layouts.

---

## Why It Matters
Chunking strategy directly controls retrieval quality, citation fidelity, and graph seeding quality. The routing decision must therefore be explicit and auditable.

---

## Inputs
- `DocumentProfile`
- canonical structure completeness score
- table density
- image density
- OCR quality
- layout irregularity score
- document length and token estimate

---

## Outputs
- `ChunkingDecision`
- primary strategy
- secondary rules
- fallback strategy

---

## Core Ideas
### Routing Variables
| Variable | Meaning |
| --- | --- |
| `structure_score` | Reliability of section, article, and clause detection. |
| `table_density` | Share of document occupied by tables or table-like content. |
| `image_density` | Share of image or scan-driven evidence. |
| `ocr_quality` | Confidence of recovered text from scans or images. |
| `layout_irregularity` | Degree of non-linear page structure. |
| `document_length` | Total size after extraction. |

### Strategy Set
- `structural`
- `semantic`
- `legal_aware`
- `table_aware`
- `mixed_group`
- `long_local_structural`
- `conservative_fallback`

---

## Pipeline
1. Read profiling and validation outputs.
2. Compute routing variables and classify the document family.
3. Select a primary chunking strategy.
4. Attach secondary rules for tables, images, or degraded OCR.
5. Define a fallback strategy if validation fails.
6. Emit a decision record before chunk generation begins.

---

## Rules
### ALWAYS
- Route based on observed document features, not file extension alone.
- Prefer structural chunking when structure confidence is strong.
- Prefer `long_local_structural` for long text-dominant legal documents with sparse complex regions.
- Switch to conservative behavior when OCR or structure confidence is low.
- Add table-aware rules whenever tables carry legal meaning.
- Preserve explainability for every routing decision.

### NEVER
- Apply semantic chunking to a strongly structured law without reason.
- Ignore degraded OCR when selecting split granularity.
- Treat image-heavy or mixed-layout documents as plain text.
- Omit a fallback path for invalid chunk outputs.
- Hide decision thresholds from logs.

---

## Decision Logic
```text
if structure_score >= high and table_density <= low and image_density <= low:
    if document_length >= long_document_threshold:
        strategy = long_local_structural
    else:
        strategy = structural
elif structure_score >= medium and document_length >= long_document_threshold:
    strategy = legal_aware
elif table_density >= high and layout_irregularity <= medium:
    strategy = table_aware
elif image_density >= medium or ocr_quality <= low:
    strategy = conservative_fallback
elif layout_irregularity >= high:
    strategy = mixed_group
else:
    strategy = semantic

secondary_rules:
    if tables exist:
        enforce table-header preservation
        if document_length >= long_document_threshold and table_density < high:
            keep text body local and create table-region override chunks
    if images contain legal evidence:
        create linked evidence chunks
    if OCR quality is low:
        avoid fine semantic splits
```

Document family guidance:
- simple text documents -> `structural`
- long legal documents -> `long_local_structural` unless structure is weak
- scanned documents -> `conservative_fallback`
- table-heavy documents -> `table_aware`
- mixed content documents -> `mixed_group`
- image-heavy documents -> `conservative_fallback` with sibling evidence chunks

Fallback strategy:
```text
if chosen strategy fails validation:
    move one level more conservative
    structural -> legal_aware
    long_local_structural -> legal_aware
    legal_aware -> semantic
    table_aware -> mixed_group
    mixed_group -> conservative_fallback
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Long statute with reliable articles but noisy annex tables | Use structural for body and table-aware overrides for annex regions. |
| Long contract with mostly plain text but a few embedded tables | Use `long_local_structural` for the body and table-aware sibling chunks for the embedded tables. |
| Short scanned contract with good OCR but low structure score | Use legal-aware chunks around visible clauses; keep conservative boundaries. |
| Image-heavy filing with sparse text labels | Use conservative fallback and linked evidence chunks only. |
| Table-heavy regulation with multi-page schedules | Use table-aware with row-group splitting and mandatory header duplication. |
| Mixed form with checkboxes and short prose | Use mixed-group to keep visual evidence aligned with nearby text. |
| Cross-jurisdiction bundle in one upload | Route per document unit, not one strategy for the full bundle. |

---

## Data Model
`ChunkingDecision` fields:
- `document_id`
- `strategy`
- `secondary_rules[]`
- `fallback_strategy`
- `routing_signals`
- `long_document_threshold`
- `decision_confidence`
- `reason_codes[]`
- `created_at`

---

## Retrieval Impact
Explicit routing improves retrieval consistency because chunk shapes match the evidence shape of the source document. This reduces false positives from overbroad semantic chunks and false negatives from oversplitting.

---

## GraphRAG Impact
The decision tree determines how cleanly chunks map to graph seeds. Conservative strategies reduce noisy node activation when source quality is degraded; structural strategies improve citation and hierarchy traversal.

---

## Logging
Always log:
- routing variables
- chosen strategy
- reason codes
- fallback usage
- validation-triggered strategy changes
- decision confidence

---

## Validation
- Validate routing reproducibility for the same profile input.
- Validate strategy alignment with benchmarked document families.
- Validate fallback activation on invalid chunk sets.
- Review misrouted cases through failure logs.
- Compare retrieval quality by strategy class.

---

## Future Improvements
- Learned routing calibration from benchmark outcomes.
- Separate strategies for legislative history and case law.
- Query-aware alternate chunk views.
- Better OCR-specific routing heuristics for low-resource languages.
