# Extraction Rules

## Goal
Define the prompt contract for AI-assisted extraction, OCR repair, table repair, and layout reconstruction when deterministic methods are insufficient.

---

## Problem
AI assistance can repair complex regions, but without strict rules it may summarize, normalize away legal nuance, or invent unreadable content.

---

## Why It Matters
Prompt rules determine whether AI acts as a bounded recovery operator or an unsafe paraphrasing layer. Extraction prompts must preserve evidence exactly.

---

## Inputs
- region crop or page crop
- local extraction result
- expected region type
- canonical output schema
- confidence thresholds and error notes

---

## Outputs
- structured extraction candidate
- repair annotations
- unresolved segments
- confidence estimate

---

## Core Ideas
### Allowed AI Actions
- reconstruct visible text layout
- repair broken OCR characters or line grouping when visually supported
- rebuild table topology from visible cells
- classify unclear regions as text, table, image, or mixed
- mark unreadable spans explicitly

### Forbidden AI Actions
- summarize source content
- rewrite clauses into simpler language
- infer hidden or blurred text
- invent table cells, headers, or article numbers
- resolve legal meaning beyond visible evidence

### Exactness Rules
- preserve original wording and numbering
- preserve line or block order when relevant
- keep uncertain characters marked as uncertain rather than guessed
- output only what can be grounded in the provided evidence

### Output Format Rules
AI output must be structured and typed. Freeform prose output is not accepted for pipeline ingestion.

---

## Pipeline
1. Package region evidence, local extraction, and failure notes.
2. Provide the AI with the exact task type: OCR repair, table repair, or layout reconstruction.
3. Require structured output only.
4. Validate the response against source evidence and schema.
5. Accept only fields that pass no-invention and structure validation.
6. Reject or downgrade any unsupported repair.

---

## Rules
### ALWAYS
- Tell the model it is repairing extraction, not interpreting law.
- Provide raw evidence and local extraction side by side.
- Require uncertain spans to remain uncertain.
- Require type-safe output for text blocks, tables, or regions.
- Validate model output before merge.

### NEVER
- Ask the model to guess missing text.
- Ask for summaries or legal explanations during extraction.
- Accept freeform prose when a schema is expected.
- Merge repaired output without source comparison.
- Let the model normalize away numbering or layout markers.

---

## Decision Logic
```text
if local extraction confidence >= threshold:
    do not call AI
elif region type is table and topology is broken:
    call AI in table-repair mode
elif OCR confidence is low but text is visually recoverable:
    call AI in OCR-repair mode
elif mixed layout prevents safe reading order:
    call AI in layout-reconstruction mode
else:
    keep unresolved and mark degraded
```

Recommended output contract:

```text
mode: ocr_repair | table_repair | layout_reconstruction
content_type: text | table | mixed
content: typed payload
uncertain_spans[]
notes[]
confidence
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Visible but ambiguous digit in article number | Return uncertainty marker, not a guessed number. |
| Table cell partly occluded by stamp | Preserve readable part and mark the rest unreadable. |
| Multi-column text mixed with side notes | Reconstruct reading order only from visible layout evidence. |
| Seal contains emblem and faint text | Extract only legible text fragments. |
| OCR produced duplicated lines | Allow deduplication only if duplicates are clearly the same visible line. |
| Handwritten edits on contract | Tag as annotation evidence, not body text replacement. |

---

## Data Model
`AIExtractionRequest` fields:
- `request_id`
- `mode`
- `region_type`
- `source_image_ref`
- `local_output`
- `schema_hint`
- `failure_notes[]`

`AIExtractionResponse` fields:
- `mode`
- `content_type`
- `content`
- `uncertain_spans[]`
- `confidence`
- `evidence_notes[]`

---

## Retrieval Impact
Strict extraction prompts reduce the chance that retrieval indexes invented or paraphrased text. That directly improves citation safety and evidence recall quality.

---

## GraphRAG Impact
Graph construction inherits extraction truthfulness. Bounded prompts prevent the graph from being built on model-generated content that was never present in the source.

---

## Logging
Always log:
- prompt mode
- reason for AI invocation
- validation outcome
- rejected unsupported fields
- uncertainty markers returned
- merge decision

---

## Validation
- Validate schema conformance.
- Validate no-invention constraints against source evidence.
- Validate numbering and structural markers.
- Validate uncertain spans are preserved.
- Spot-check rejected outputs to refine prompts.

---

## Future Improvements
- Specialized prompts per document family.
- Better uncertainty encoding for partially legible text.
- Multi-pass prompts with deterministic post-validation only.
- Prompt libraries for recurring legal table templates.
