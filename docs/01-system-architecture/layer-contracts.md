# Layer Contracts

## Goal
Define stable contracts between layers so agents can implement without cross-module drift.

## Contract Overview
| Producer | Consumer | Contract |
| --- | --- | --- |
| Document Intelligence | Knowledge Structuring | Blocks, tables, images, page refs, confidence, provenance. |
| Knowledge Structuring | Chunking | Section/article/clause hierarchy and canonical refs. |
| Chunking | Retrieval | Chunks with content, anchors, citations, language, metadata, confidence. |
| Graph Builder | Retrieval | Nodes and edges with provenance and confidence. |
| Retrieval | Reasoning | Ranked evidence set with citations and support signals. |
| Reasoning | Action Engine | Evidence-bounded reasoning result. |

## Canonical Strategy Names
Extraction strategies:
- `simple_local`: clean, short, text-first documents.
- `long_local`: long text-dominant documents.
- `hybrid_region_precision`: mixed documents where specific regions need table/image/scan handling.
- `scan_recovery`: scan-heavy documents requiring OCR and confidence gating.

Chunking strategies:
- `structural`
- `long_local_structural`
- `legal_aware`
- `table_aware`
- `mixed_group`
- `conservative_fallback`

## Required Artifact Fields
Every evidence-bearing artifact must carry:
- `document_id`
- `trace_id`
- `source_hash`
- source location or page reference
- confidence
- degraded status when quality is low
- processing version

## Configuration Contract
The implementation must centralize thresholds in `src/config.py`.

Required controls:
- `enable_ocr`
- `enable_ai_repair`
- `strict_accuracy_mode`
- `parser_noise_cleanup`
- `strong_text_layer_threshold`
- `weak_text_layer_threshold`
- `long_document_page_threshold`
- `long_document_token_threshold`
- `table_topology_threshold`
- `ocr_confidence_threshold`
- `chunk_authority_threshold`

## Logging Contract
Every stage must log:
- start and end
- routing decisions
- thresholds used
- warnings and failures
- output counts
- degraded evidence signals

Log fields must not conflate:
- severity: `info`, `warning`, `error`
- stage status: `pass`, `warning`, `fail`, `skipped`

## Validation Contract
The system must validate:
- source coverage
- non-empty blocks
- table preservation
- chunk boundaries
- graph provenance
- retrieval smoke tests
- hallucination risk signals

