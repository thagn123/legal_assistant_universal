# Chunking Strategies

## Goal
Define chunk construction strategies for legal retrieval that preserve hierarchy, legal meaning, citations, tables, and nearby context without introducing unsupported recombination.

---

## Problem
Naive token-window chunking breaks article boundaries, separates conditions from exceptions, strips table headers, and weakens both retrieval precision and downstream answer grounding.

---

## Why It Matters
Chunking is the bridge between extraction and retrieval. If chunks do not align with legal units, the system will retrieve semantically similar but legally incomplete content.

---

## Inputs
- Canonical structured document objects.
- Ordered blocks with section, article, clause, table, and image references.
- Token and size constraints for indexing.
- Retrieval workload assumptions: factual lookup, drafting, comparison, risk analysis.

---

## Outputs
- `ChunkSet`
- chunk metadata and overlap metadata
- chunk-to-structure links
- chunk-to-graph seed links

---

## Core Ideas
### Primary Chunking Modes
| Strategy | Use |
| --- | --- |
| Structural chunking | Default for well-formed legal hierarchy. |
| Semantic chunking | Use when structure is weak but paragraph transitions are strong. |
| Legal-aware chunking | Preserve operative units such as definitions, obligations, exceptions, penalties, and amendment text. |
| Table-aware chunking | Keep table structure intact and attach explanatory context. |
| Mixed-document chunking | Combine text, tables, images, and annex references under coordinated chunk groups. |

### Boundary Principles
- Prefer article or clause completion over equal token length.
- Repeat minimal hierarchy context into child chunks.
- Separate normative text from commentary or footnotes unless directly coupled.
- Preserve cross-reference anchors inside each chunk.
- Exclude parser trash and mechanically duplicated fragments from retrieval-facing chunk bodies while retaining raw traceability upstream.

### What Must Never Be Split
- Article number from article title and opening text.
- Clause condition from its operative consequence when the clause is short enough to stay whole.
- Table header context from table rows that depend on it.
- Definition term from its definition text.
- Amendment instruction from the target citation it modifies.

### Context Preservation
Each chunk should include:
- structural path
- jurisdiction and document metadata
- local citations
- parent heading context
- preceding or following overlap only when it changes meaning
- linked table or image evidence references when the legal meaning depends on them

### Size Guidance
- Prefer one complete article, clause group, or logical table as the base chunk.
- Split only when the legal unit materially exceeds model or index limits.
- Use overlap based on structure, not fixed tokens.

---

## Pipeline
1. Receive canonical ordered blocks.
2. Classify document shape: structured text, table-heavy, mixed, scan-derived, or weak-structure.
3. Select primary chunking mode.
4. Group blocks by structural path and legal completeness.
5. Attach tables and images either inline or as linked sibling chunks based on dependency strength.
6. Apply limited overlap using parent headings, definitions, or cross-reference context.
7. Compute chunk metadata, token estimate, citations, and structure anchors.
8. Validate that chunk boundaries do not sever mandatory legal dependencies.
9. Emit `ChunkSet` and retrieval projections.

---

## Rules
### ALWAYS
- Chunk from canonical structure, not raw page text.
- Carry structural path and source anchors into every chunk.
- Preserve tables and definitions as explicit retrieval units.
- Duplicate minimal context when splitting large legal units.
- Keep version and jurisdiction metadata on every chunk.
- Keep long-document context by repeating the minimal parent article or clause path needed for interpretation.

### NEVER
- Split solely at fixed token intervals.
- Merge unrelated articles because they fit within one token budget.
- Drop clause numbering during chunk normalization.
- Flatten a table into narrative-only text for the main chunk body.
- Build chunks from low-confidence text without degradation markers.
- Let parser duplicates or OCR garbage survive into final chunks when they can be safely suppressed.

---

## Decision Logic
```text
if document has reliable hierarchy:
    use structural chunking
    if article exceeds size limit:
        split by clause or subclause with heading carryover
elif hierarchy is weak but paragraph transitions are clear:
    use semantic chunking with legal boundary guards

if table is legally central:
    create dedicated table chunk plus contextual parent chunk
if long document is mostly plain text with sparse complex regions:
    keep local structural chunks for the body and create linked sibling chunks for table or image regions
if document mixes text, image, and table evidence in one legal unit:
    create chunk group with one primary text chunk and linked sibling evidence chunks
if scan-derived text has low confidence:
    restrict chunk eligibility for authoritative answering
```

Overlap rules:
- heading overlap: always allowed
- definition overlap: allowed when referenced by child clauses
- clause overlap: allowed only for split clauses
- table header overlap: mandatory for row-split tables

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| One article spans many pages | Split by clause or enumerated items; repeat article heading and citation path. |
| Long clause with inline table | Keep clause text as primary chunk and link the table as sibling evidence if the full unit exceeds size limits. |
| Long document with a few complex exhibits | Keep main legal flow chunked structurally and attach exhibit chunks only where referenced. |
| Bilingual aligned contract | Chunk per language stream, then cross-link equivalent chunks when alignment confidence is high. |
| Annex referenced by main clause | Keep annex as separate chunk set and add explicit back-reference links. |
| OCR-degraded scanned regulation | Chunk conservatively and mark degraded confidence; avoid fine semantic splits. |
| Bullet list of exceptions under one clause | Keep list with its governing clause introduction. |

---

## Data Model
`Chunk` minimum fields:
- `chunk_id`
- `document_id`
- `chunk_type`
- `content_format`
- `content`
- `structure_path`
- `page_refs[]`
- `block_refs[]`
- `table_refs[]`
- `image_refs[]`
- `citations[]`
- `parent_chunk_id`
- `sibling_chunk_ids[]`
- `overlap_from[]`
- `token_estimate`
- `confidence`
- `degraded`

---

## Retrieval Impact
Strategy choice changes retrieval precision and recall:
- structural chunking improves direct clause lookup
- semantic chunking improves weakly structured documents
- table-aware chunking improves exact row retrieval
- mixed-document chunk groups improve evidence completeness

---

## GraphRAG Impact
Chunk boundaries influence which graph nodes are seeded during retrieval. Structure-preserving chunks create cleaner structural and citation seed sets and reduce noisy graph expansion.

---

## Logging
Always log:
- chosen chunking strategy
- split reasons
- overlap reasons
- chunk token estimates
- degraded chunk flags
- table or image sibling linkage
- parser-noise suppression that affected chunk content

---

## Validation
- Validate that every chunk maps to at least one structural unit.
- Validate that prohibited splits did not occur.
- Validate that chunk content is contiguous in source order unless explicitly grouped.
- Validate overlap size and rationale.
- Benchmark chunk retrieval on clause, table, and citation queries.

---

## Future Improvements
- Adaptive chunking learned from retrieval performance.
- Better cross-document clause alignment chunks.
- Jurisdiction-specific legal unit detectors.
- Query-intent-conditioned secondary chunk projections.
