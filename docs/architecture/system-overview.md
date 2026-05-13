# System Overview

## Goal
Describe the complete end-to-end architecture for ingesting legal documents, converting them into structured knowledge assets, and serving grounded legal assistance through hybrid retrieval and GraphRAG.

---

## Problem
The platform must support diverse legal files while balancing accuracy, cost, speed, and hallucination control. A monolithic parser or pure vector-search architecture cannot reliably preserve legal structure, citations, tables, and cross-document relations.

---

## Why It Matters
Architecture determines whether legal evidence remains recoverable. Each module must produce outputs that are both machine-usable and legally traceable, otherwise later reasoning stages cannot be trusted.

---

## Inputs
- Uploaded source files and optional metadata hints.
- Processing configuration: thresholds, enabled extractors, supported output format.
- User queries for Q&A, drafting support, clause retrieval, risk analysis, and comparison.

---

## Outputs
- Raw source archive.
- Profile and complexity assessment.
- Canonical structured document representation.
- Validated chunk set.
- Legal knowledge graph.
- Search indexes and retrieval evidence sets.
- Citation-backed answer packages.

---

## Core Ideas
### Module Map
| Module | Responsibility |
| --- | --- |
| Upload Gateway | Receive file, validate type, assign identifiers, archive source. |
| Document Profiler | Detect file format, page count, text layer, language hints, scan quality, layout signals. |
| Complexity Router | Choose local, hybrid, or AI-assisted extraction per document and region, with long-form local and precision-critical table or image overrides. |
| Layout Analyzer | Segment pages into typed regions with reading order and confidence. |
| Extraction Engine | Extract text, tables, images, and structural signals from each region. |
| Cleaning and Validation | Normalize mechanically, reconcile ordering, and reject unsupported repairs. |
| Structuring Engine | Build section, article, clause, table, and image objects in the canonical schema. |
| Chunking Engine | Create retrieval units without breaking legal meaning. |
| Graph Builder | Create nodes and edges for hierarchy, citations, entities, and legal relations. |
| Indexing Layer | Store vector, keyword, metadata, and graph access structures. |
| Retrieval Orchestrator | Route queries and combine vector, keyword, metadata, and graph retrieval. |
| Reasoning and Response Layer | Produce grounded outputs with citation, confidence, and refusal behavior. |
| Parser QA Layer | Run parse validation, noise detection, benchmark hooks, and regression logging. |

### Architectural Principles
- Per-region routing is preferred over document-wide AI escalation.
- The canonical document schema is the handoff contract between ingestion and retrieval.
- Retrieval must be multimodal in evidence type, not only in embedding space.
- Graph edges are evidence-bearing only when provenance is explicit.

---

## Pipeline
1. Upload Gateway stores the raw file and creates `document_id`.
2. Document Profiler computes format, text-layer coverage, language hints, page count, scan quality, and region priors.
3. Complexity Router assigns a document strategy and optional per-page or per-region overrides.
4. Layout Analyzer segments each page into ordered regions.
5. Extraction Engine runs local extractors first for plain and long-form text, then AI-assisted repair or verification for failed, complex, table, or image regions only.
6. Structuring Engine maps extracted content into blocks, sections, articles, clauses, tables, images, and metadata.
7. Cleaning and Validation checks coverage, ordering, broken numbering, duplicate blocks, OCR noise, parser trash, and unresolved low-confidence content.
8. Chunking Engine emits retrieval chunks with structure-aware overlap and source anchors.
9. Graph Builder creates structural, citation, entity, and semantic edges with provenance and confidence.
10. Indexing Layer writes vector embeddings, keyword indexes, metadata filters, and graph adjacency data.
11. Retrieval Orchestrator classifies queries and selects vector, keyword, metadata, graph, or hybrid retrieval.
12. Reasoning Layer assembles evidence, validates support sufficiency, and generates a cited response or refusal.

---

## Rules
### ALWAYS
- Archive the original file before any transformation.
- Keep intermediate artifacts versioned and traceable.
- Separate deterministic extraction from probabilistic repair.
- Preserve region-level routing decisions so long documents can stay mostly local while table or image regions get higher-precision treatment.
- Propagate page anchors and block identifiers into chunks and graph nodes.
- Validate evidence sufficiency before response generation.

### NEVER
- Skip profiling and route directly to a model for all documents.
- Destroy or overwrite raw extraction with cleaned text.
- Create graph edges without provenance.
- Embed or rank content that failed minimum validation without labeling it degraded.
- Generate final legal claims from retrieval results that lack citation anchors.

---

## Decision Logic
- If a document has strong text-layer coverage and low complexity, use local-first extraction for the full document.
- If only specific regions are complex, run hybrid extraction and keep unaffected regions local.
- If a long document is text-dominant but contains sparse tables or images, use long-form local extraction for the body and region overrides for those precision-critical zones.
- If the document is scan-heavy with low OCR confidence, allow region-level AI-assisted reconstruction after local OCR fails.
- If structure parsing and text extraction disagree, preserve both artifacts, prefer source-faithful text, and flag the structure for validation.
- If query intent requires direct authority lookup, prioritize structural and citation-aware retrieval over broad semantic expansion.

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Encrypted PDF with extractable text disabled | Preserve file, mark extraction blocked, request a decryptable source or perform approved render-based OCR if policy allows. |
| Document bundle with annexes | Treat annexes as subordinate structures, not separate chunks mixed into the main body. |
| Mixed-language contract with bilingual columns | Preserve each column order and cross-link aligned clauses when alignment is confident. |
| Table spans multiple pages | Store one logical table with page-sliced provenance and continuation markers. |
| Image-only signature page | Keep as image evidence; do not fabricate signer names unless OCR or metadata provides them. |
| Duplicate numbered clauses caused by OCR drift | Preserve raw extraction, attempt repair, and flag unresolved numbering conflicts. |

---

## Data Model
Primary data flow contract:

```text
UploadRequest
  -> DocumentProfile
  -> PageRegions[]
  -> ExtractedBlocks[]
  -> CanonicalDocument
  -> ChunkSet
  -> GraphSubgraph
  -> RetrievalEvidence
  -> AnswerPackage
```

Critical identifiers:
- `document_id`
- `page_id`
- `region_id`
- `block_id`
- `section_id`
- `chunk_id`
- `node_id`
- `trace_id`

---

## Retrieval Impact
This architecture enables retrieval to use the right evidence unit for the query: clause text, table rows, citations, definitions, or linked authorities. Poor architecture would force retrieval to operate on flattened paragraphs with weak source anchors.

---

## GraphRAG Impact
Graph quality depends on structured ingestion. Hierarchy, citation chains, definitions, and references are easier to model when extraction artifacts preserve region identity and legal structure before chunking.

---

## Logging
Always log:
- Module start and end status with `trace_id`.
- Strategy choices and threshold values.
- Per-page and per-region extraction path.
- Validation failures and downgraded artifacts.
- Retrieval plan and answer support summary.

---

## Validation
- Verify that every architecture module has a defined input and output contract.
- Verify that source anchors survive from ingestion through response generation.
- Verify that the architecture supports local-first extraction and selective AI escalation.
- Verify that failure states do not silently fall through to unsupported answers.

---

## Future Improvements
- Streaming ingestion for large document collections.
- Incremental graph updates for amended laws and contract revisions.
- Jurisdiction-specific retrieval rankers.
- Human-in-the-loop correction queue for low-confidence structural artifacts.
