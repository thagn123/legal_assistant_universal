# Adaptive Document Intelligence Pipeline

## Goal
Convert legal files into structured legal knowledge while preserving source fidelity, hierarchy, tables, images, and traceability.

## Supported Inputs
- PDF
- scanned PDF
- DOCX
- legacy DOC
- HTML
- TXT
- image files
- mixed legal document bundles

## Supported Outputs
- canonical structured JSON objects
- Markdown
- HTML
- semantic chunks
- graph-ready nodes and edges
- evaluation and debug logs

## Pipeline
```text
File
  -> Detect format
  -> Profile text layer, length, tables, images, layout, OCR need
  -> Choose extraction strategy
  -> Segment layout into regions
  -> Extract each region
  -> Clean parser noise
  -> Validate completeness and fidelity
  -> Emit canonical document
```

## Extraction Strategy
| Strategy | Use When | Behavior |
| --- | --- | --- |
| `simple_local` | Clean text document with low complexity. | Use deterministic local extraction. |
| `long_local` | Long legal text with stable structure. | Keep main body local; avoid whole-document AI. |
| `hybrid_region_precision` | Tables, images, mixed layout, or local failures exist. | Route only complex regions to strict repair. |
| `scan_recovery` | Text layer is weak or missing. | Run OCR and gate by confidence. |

## Local-First Rules
Always use local extraction for:
- clean PDFs
- long text-first legal documents
- DOCX/HTML with accessible structure
- simple tables that deterministic tools preserve correctly

## AI-Assisted Rules
AI assistance may be used only when enabled and bounded:
- table topology repair
- OCR cleanup for visible text
- image text extraction
- mixed layout reconstruction

AI assistance must not:
- invent missing content
- summarize legal meaning
- rewrite legal clauses
- create citations
- fill unreadable table cells

## Parser Noise Policy
Parser noise includes:
- duplicate short headers or footers
- page-number artifacts
- OCR garbage fragments
- broken line ordering artifacts
- repeated table-of-content fragments

Required behavior:
- preserve raw extraction separately
- remove noise from retrieval-facing text only when safe
- log cleanup actions
- never delete legally meaningful repeated text automatically

## Validation Gates
Reject or degrade outputs when:
- no blocks are extracted from a non-empty source
- page coverage is suspiciously low
- OCR confidence is below threshold
- table topology is not preserved
- source anchors are missing
- cleanup changes cannot be justified

