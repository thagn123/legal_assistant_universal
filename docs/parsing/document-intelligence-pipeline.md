# Document Intelligence Pipeline

## Goal
Define the end-to-end document processing pipeline that profiles legal files, routes extraction by complexity, preserves structure, and emits validated HTML or Markdown plus canonical structured objects.

---

## Problem
Legal documents mix plain text, scans, tables, diagrams, seals, headers, footers, and multilingual content. A single parser path either loses fidelity on complex regions or wastes cost by sending simple documents through AI.

---

## Why It Matters
Extraction is the evidence foundation for retrieval and GraphRAG. If the system drops numbering, table structure, or citations at this stage, later components cannot reconstruct authoritative meaning.

---

## Inputs
- Source file: PDF, scanned PDF, DOCX, HTML, image, image bundle.
- Optional metadata hints: jurisdiction, language, document type, source date.
- Page renderings or region crops produced during profiling.
- Policy thresholds for OCR, layout irregularity, and AI escalation.

---

## Outputs
- `DocumentProfile`
- `ExtractionPlan`
- `CanonicalDocument`
- Normalized output in `html` or `markdown`
- Extraction diagnostics with provenance, confidence, and unresolved issues

---

## Core Ideas
### Profiling Before Extraction
Every file is profiled before extraction begins. Profiling determines:
- file format and container type
- text-layer availability and coverage
- page count and size variability
- presence of tables, images, and mixed layouts
- scan quality and OCR need
- likely language set
- document complexity score

### Local-First Extraction
Local extraction is the default for:
- text PDFs with strong text-layer coverage
- long legal documents with stable hierarchy
- DOCX or HTML files with recoverable semantic structure
- tables that can be extracted with deterministic tools

### Long-Document Policy
Long-form legal documents use local extraction for the main text body by default. This prevents unnecessary model cost, improves determinism, and reduces hallucination risk. Region-level overrides are allowed when:
- a table appears inside an otherwise plain long document
- an embedded image contains legally relevant text
- a scan-derived appendix degrades local fidelity

### Precision-Critical Region Policy
The following regions are precision-critical and may receive stricter escalation than body text:
- tables carrying operative legal data
- image or scan regions containing text
- mixed regions that break reading order
- annex schedules where local extraction loses topology or numbering

### Selective AI Assistance
AI assistance is allowed only for:
- low-confidence OCR repair
- table reconstruction when cell topology is broken
- layout reconstruction in mixed or multi-column regions
- image text extraction from visually complex regions
- optional verification of table or image extraction in high-accuracy mode, limited to source-grounded comparison and repair

### Output Formats
- `html`: preferred when preserving nested structure, tables, inline references, and rich anchors.
- `markdown`: acceptable for text-first retrieval, simple tables, and human-readable review.
- Canonical internal objects remain the source of truth; HTML or Markdown are derived views.

---

## Pipeline
1. Validate source file and compute `source_hash`.
2. Detect file type and container characteristics.
3. Profile the document for text-layer coverage, scan quality, layout complexity, tables, images, and language hints.
4. Build an `ExtractionPlan` with document-level defaults and region-level overrides.
5. Classify the document into one of: `simple_local`, `long_local`, `hybrid_region_precision`, `scan_recovery`.
6. Render page images only when required for OCR, layout analysis, or visual regions.
7. Run layout analysis to segment pages and assign reading order.
8. Extract text from text regions using local parsers.
9. Extract tables using deterministic table parsers when topology is recoverable.
10. Run OCR on scan or image regions.
11. Apply AI-assisted repair only to failed or low-confidence regions, or to precision-critical table or image regions under strict mode.
12. Run parser-noise cleanup to remove duplicated lines, broken headers or footers, isolated OCR garbage, and ordering artifacts without changing legal wording.
13. Merge ordered region outputs into block sequences.
14. Detect hierarchy: headings, articles, clauses, schedules, annexes, footnotes, citations.
15. Emit canonical structured objects with provenance and confidence.
16. Generate normalized HTML or Markdown from canonical objects.
17. Run validation on coverage, order, structure, table integrity, parser noise, and unsupported repairs.

---

## Rules
### ALWAYS
- Detect file type and text-layer state before choosing extraction mode.
- Keep raw extraction artifacts separate from cleaned outputs.
- Perform OCR only where needed; avoid OCR over usable text layers.
- Preserve original order, numbering, and page references.
- Escalate at region level before escalating the whole document.
- Strip parser trash from retrieval-facing clean outputs while preserving raw evidence.

### NEVER
- Use AI for the entire document when only a few regions are complex.
- Replace missing text with inferred text.
- Collapse tables into prose when structural preservation is possible.
- Suppress low-confidence warnings from downstream consumers.
- Emit final HTML or Markdown without canonical provenance anchors.
- Let cleanup remove legally meaningful text just because it looks repetitive.

---

## Decision Logic
```text
if file_type in {docx, html}:
    extract structure locally
elif pdf and text_layer_coverage >= strong_threshold and layout_complexity <= medium:
    if document_length >= long_document_threshold:
        use long_local extraction
    else:
        use local-first extraction
elif pdf and text_layer_coverage < weak_threshold:
    classify as scan-heavy
    run OCR on page or region basis
else:
    use hybrid extraction

for each region:
    if region_type == table and table_confidence >= table_threshold:
        use deterministic table parser
        if strict_accuracy_mode:
            verify or repair with bounded AI assistance
    elif region_type == table:
        use AI-assisted table repair
    elif region_type == image:
        run OCR
        if ocr_confidence < image_text_threshold or strict_accuracy_mode:
            use AI-assisted image text extraction
    elif region_type == mixed:
        use layout reconstruction with strict no-invention rules
    else:
        keep local extraction output
```

Routing thresholds:
- `strong_text_layer`: high visible text coverage with low OCR need
- `weak_text_layer`: sparse or empty extractable text
- `long_document_threshold`: size threshold above which body text should remain local unless regions override
- `table_threshold`: minimum topology confidence for deterministic preservation
- `ocr_threshold`: minimum acceptable OCR confidence for authoritative text use

---

## Edge Cases
| Case | Fallback Behavior |
| --- | --- |
| Text PDF with image-only appendix | Keep main body local; OCR appendix only. |
| Long law with a few embedded schedules | Keep body in `long_local`; route schedules through table-aware extraction and preserve linkage to parent articles. |
| Scanned contract with handwritten notes | Extract printed text, isolate handwriting as image evidence, do not merge handwritten interpretation into body text. |
| Multi-column statute with footnotes | Use layout analysis before text merge; preserve footnotes as separate linked blocks. |
| Broken OCR on article numbering | Preserve raw output, attempt targeted repair, flag unresolved numbering ambiguity. |
| Spreadsheet exported to PDF | Treat dense grid regions as tables first, not paragraphs. |
| Embedded stamp covering text | Mark occluded text as incomplete if unreadable after OCR and repair. |

---

## Data Model
Pipeline control objects:

```text
DocumentProfile
  file_type
  text_layer_coverage
  scan_quality_score
  layout_complexity_score
  table_density
  image_density
  languages[]

ExtractionPlan
  document_strategy
  page_overrides[]
  region_overrides[]
  output_format
  strict_accuracy_mode
  parser_noise_cleanup
```

Canonical outputs must reference:
- `document_id`
- `page_id`
- `region_id`
- `block_id`
- `source_offsets`
- `confidence`
- `repair_status`

---

## Retrieval Impact
The pipeline determines whether retrieval sees meaningful legal units or damaged text blobs. Table-preserving and structure-preserving extraction improves both lexical and semantic recall for clause lookup, risk detection, and drafting support.

---

## GraphRAG Impact
Hierarchy recovery, citation capture, and explicit region typing give the graph builder reliable material for structural edges, citation edges, and evidence-bearing semantic edges.

---

## Logging
Always log:
- file type and text-layer decision
- document strategy: `simple_local`, `long_local`, `hybrid_region_precision`, or `scan_recovery`
- document and region complexity scores
- OCR confidence and repair attempts
- AI escalation reasons
- parser-noise cleanup actions
- output format choice
- unresolved extraction defects

---

## Validation
- Verify page coverage against the source page count.
- Verify reading order continuity within each page.
- Verify that every emitted block has provenance.
- Verify that AI-assisted outputs do not add unsupported content.
- Verify that cleaned outputs do not contain duplicate lines, footer noise, or orphan OCR fragments unless preserved in raw artifacts only.
- Verify HTML or Markdown regeneration from canonical objects is loss-bounded.

---

## Future Improvements
- Better handwriting isolation for annotations.
- Learned cost-aware routing policies.
- Language-specific hierarchy detection packs.
- Region-level active learning from validation failures.
- In long documents, detect table or image subregions more aggressively while keeping the main body fully local.
