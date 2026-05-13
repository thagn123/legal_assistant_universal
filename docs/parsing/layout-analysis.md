# Layout Analysis

## Goal
Define how the system segments pages into ordered regions, measures layout regularity, and produces region metadata used by extraction routing and structure reconstruction.

---

## Problem
Legal pages often contain multi-column text, side notes, tables, stamps, signatures, headers, footers, and mixed visual artifacts. Naive top-to-bottom text extraction breaks reading order and corrupts legal meaning.

---

## Why It Matters
Layout analysis decides where content begins and ends before extraction. Accurate region detection prevents cross-column mixing, table flattening, misplaced footnotes, and citation drift.

---

## Inputs
- Page image or render.
- Optional text-layer boxes from local PDF extraction.
- Page geometry, font and spacing hints, and image masks.
- Profiling thresholds for region classification and irregularity scoring.

---

## Outputs
- Ordered `PageRegion[]`
- `reading_order`
- `layout_irregularity_score`
- region confidence and failure flags

---

## Core Ideas
### Region Types
| Region Type | Definition |
| --- | --- |
| Text | Continuous prose or structured numbered text. |
| Table | Grid-like content with row and column semantics. |
| Image | Non-table visual region such as seal, signature, diagram, scanned page crop, or embedded figure. |
| Mixed | Region containing overlapping text, graphics, sidebars, or unresolved structure. |

### Page Segmentation
Segmentation proceeds from coarse to fine:
1. detect margins, headers, footers, and body zones
2. split columns and major containers
3. detect region candidates
4. refine boundaries by overlap, whitespace, and text box grouping
5. assign region type and confidence

### Reading Order
Reading order is computed from:
- column structure
- vertical and horizontal alignment
- numbering continuity
- footnote markers
- table continuation markers

### Confidence Scoring
Region confidence combines:
- detector certainty
- text box alignment quality
- box overlap rate
- topology consistency
- OCR or text-layer agreement

### Layout Irregularity Detection
Irregularity increases when:
- columns cross or overlap
- region boundaries are unstable across adjacent pages
- text boxes interleave between unrelated areas
- dense visual overlays hide text
- table and paragraph signals conflict

---

## Pipeline
1. Render or access page geometry.
2. Detect header, footer, margin, and body zones.
3. Detect text lines, blocks, ruling lines, images, and table candidates.
4. Group detected elements into region candidates.
5. Classify each region as text, table, image, or mixed.
6. Resolve overlaps by priority and evidence strength.
7. Compute reading order within and across columns.
8. Score layout irregularity at page and document level.
9. Emit `PageRegion[]` with bounding boxes, order, confidence, and fallback flags.

---

## Rules
### ALWAYS
- Treat layout analysis as a separate stage before region extraction in non-trivial pages.
- Keep headers, footers, and footnotes identifiable even when excluded from main reading order.
- Preserve bounding boxes and ordering metadata for every region.
- Prefer stable region boundaries over aggressive fragmentation.
- Mark unresolved overlap as `mixed` instead of forcing a wrong type.

### NEVER
- Merge parallel columns into one text flow without ordering evidence.
- Classify a region as text when grid signals strongly indicate a table.
- Drop stamps or signatures that may affect legal validity.
- Hide ambiguous layout decisions from downstream modules.
- Use layout confidence as a substitute for text extraction confidence.

---

## Decision Logic
```text
if page has single dominant text column and low overlap:
    use simple reading order
elif page has multiple columns with consistent separators:
    assign column-based reading order
elif region shows grid lines or aligned cell clusters:
    classify as table candidate
elif region contains text over image or overlapping containers:
    classify as mixed
else:
    keep conservative segmentation and escalate uncertain regions
```

Irregularity scoring guidance:
- low: stable single-column or predictable two-column layout
- medium: minor sidebars, footnotes, or tables
- high: overlapping regions, forms, stamps, heavy annotations, or inconsistent columns

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Footnote references inline with body text | Keep footnotes separate and link markers to footnote blocks. |
| Rotated appendix page | Detect orientation before region classification. |
| Two-column bilingual agreement | Preserve per-column order and do not interleave lines across languages. |
| Table without visible grid lines | Use alignment clusters and whitespace topology before giving up. |
| Full-page scanned image with faint text | Mark as image or mixed, then hand off to OCR flow. |
| Margin annotations from reviewer | Preserve as separate image or text-note regions, not as body text. |

---

## Data Model
`PageRegion` fields:
- `region_id`
- `page_id`
- `type`
- `bbox`
- `reading_order_index`
- `column_index`
- `parent_region_id`
- `confidence`
- `irregularity_flags[]`
- `source_features`

---

## Retrieval Impact
Good layout analysis preserves the locality and adjacency patterns that legal retrieval needs, especially for clause numbering, footnotes, and table-row lookups.

---

## GraphRAG Impact
Region types and ordering improve graph creation for hierarchy, citation attachment, table-row nodes, and evidence linking back to exact page areas.

---

## Logging
Always log:
- page segmentation version
- region count by type
- overlap conflicts
- reading order strategy
- layout irregularity score
- unresolved mixed regions

---

## Validation
- Validate that region bounding boxes stay within page bounds.
- Validate non-decreasing reading order indexes.
- Validate header/footer separation on pages where such zones exist.
- Validate agreement between region type and extraction behavior.
- Sample-review high-irregularity pages.

---

## Future Improvements
- Learned models for jurisdiction-specific forms.
- Better cross-page continuity for table and annex segmentation.
- Separate handwriting region classification.
- Visual lineage tracking for amendments and stamps.
