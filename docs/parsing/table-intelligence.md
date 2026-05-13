# Table Intelligence

## Goal
Define how the system detects, extracts, repairs, represents, and retrieves tables in legal documents without losing row, column, header, or cell semantics.

---

## Problem
Legal tables often carry obligations, fee schedules, deadlines, parties, sanctions, annex mappings, and compliance matrices. Flattening them into prose destroys meaning and makes citations unreliable.

---

## Why It Matters
Tables are frequently the highest-density evidence objects in legal material. Retrieval, drafting, and risk analysis all degrade when merged cells, headers, or continuation rows are mishandled.

---

## Inputs
- Table candidate regions from layout analysis.
- Source page images and text boxes.
- Deterministic parser outputs and topology signals.
- OCR output for image-based or scanned tables.

---

## Outputs
- Canonical `TableObject`
- HTML and Markdown table renderings when supported
- table-to-text retrieval projection
- repair diagnostics and unresolved topology flags

---

## Core Ideas
### Table Detection
Table signals include:
- explicit grid lines
- aligned text clusters
- repeated row baselines
- header-like top rows
- consistent column boundaries

### Structural Preservation
Preserve:
- merged cells
- header rows and header columns
- row and column order
- blank cells when legally meaningful
- continuation markers across pages

### Legal Table Handling
Common legal table classes:
- fee or penalty schedules
- obligations by role or date
- definitions matrix
- annex mapping tables
- compliance checklists
- signature or approval grids

### Output Strategy
| Output | Use |
| --- | --- |
| Canonical table object | Source of truth for downstream systems. |
| HTML table | Preferred for faithful structure and merged cells. |
| Markdown table | Allowed for simple topology only. |
| Table-to-text projection | Supplemental retrieval surface; never replaces the table object. |

### AI Repair Scope
AI may repair topology, infer missing cell boundaries from visible evidence, and normalize OCR noise. AI may not invent hidden or unreadable cell content.

---

## Pipeline
1. Receive table candidate region.
2. Detect table boundaries and internal cell topology.
3. Extract cell text with local text extraction or OCR.
4. Identify headers, spanning cells, footnotes, and continuation markers.
5. Build canonical table object.
6. Score topology confidence and content confidence.
7. If topology confidence is low, run AI-assisted repair on the region crop and current cell map.
8. Re-validate repaired table against the source image.
9. Emit HTML table where structure is representable.
10. Emit Markdown only when merged-cell loss is acceptably low.
11. Build table-to-text projection for retrieval and graph linking.

---

## Rules
### ALWAYS
- Keep tables as first-class objects.
- Preserve row and column semantics even when text projection is also generated.
- Represent merged cells explicitly.
- Keep original cell text and cleaned cell text separately when OCR normalization occurs.
- Link every cell back to page and bounding box provenance.

### NEVER
- Convert complex tables directly into plain paragraphs as the only output.
- Fill unreadable cells with guesses.
- Drop empty cells when emptiness may indicate an exception or missing obligation.
- Treat repeated header rows as duplicated data rows without validation.
- Output Markdown for topology that requires rowspans or colspans unless loss is declared.

---

## Decision Logic
```text
if table topology is explicit and cell confidence is high:
    preserve locally
elif table topology is recoverable but OCR is weak:
    OCR locally, then repair cells if needed
elif table has nested headers, merged cells, or no visible lines:
    use AI-assisted topology repair
if html can preserve structure:
    emit html
if markdown cannot preserve structure without distortion:
    emit markdown_summary = disallowed
```

Chunking rule triggers:
- keep entire small tables in one chunk
- split large tables by row groups only if header context is duplicated
- never split a merged-header dependency from its child rows without repeating header context

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Table spans multiple pages | Preserve as one logical table with continuation metadata and repeated header linkage. |
| Nested table inside a cell | Preserve parent cell and nested structure; do not flatten unless explicitly marked degraded. |
| Rotated landscape table | Rotate before extraction and keep orientation metadata. |
| Signature matrix with blank cells | Keep blanks because they may indicate missing approval. |
| Table with footnotes | Represent footnotes as linked subordinate objects, not cell text concatenation only. |
| Borderless comparison matrix | Use alignment-based topology reconstruction before escalation. |

---

## Data Model
`TableObject` minimum fields:
- `table_id`
- `document_id`
- `page_refs[]`
- `bbox_refs[]`
- `title`
- `headers`
- `rows`
- `cells`
- `row_count`
- `column_count`
- `merged_ranges[]`
- `continuation`
- `content_confidence`
- `topology_confidence`
- `repair_status`
- `source_trace`

Optional `TableCell` fields:
- `row_index`
- `column_index`
- `rowspan`
- `colspan`
- `raw_text`
- `clean_text`
- `bbox`
- `confidence`

---

## Retrieval Impact
Table-aware retrieval allows queries such as fee lookups, deadline thresholds, and party-obligation crosswalks to hit exact rows instead of unrelated nearby prose. Table-to-text projection broadens recall while the table object preserves authority.

---

## GraphRAG Impact
Tables can produce graph nodes for rows, header concepts, obligations, thresholds, and referenced entities. Structural provenance prevents graph edges from misattributing a cell value to the wrong party or condition.

---

## Logging
Always log:
- table detection score
- topology extraction method
- merged-cell count
- repair attempts
- html vs markdown emission decision
- table chunking decisions

---

## Validation
- Validate row and column counts against detected topology.
- Validate merged ranges do not exceed bounds.
- Validate header assignment consistency.
- Validate repaired tables against the source crop.
- Validate table-to-text projections preserve row identity.

---

## Future Improvements
- Better borderless table detection.
- Domain-specific legal table templates.
- Cell-level contradiction detection across amendments.
- Improved table comparison across document versions.
