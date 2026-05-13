# Project Context

## Goal
Define the system vision, boundaries, terminology, and non-negotiable operating rules for a legal multimodal GraphRAG platform.

---

## Problem
Legal documents vary by jurisdiction, language, format, layout quality, and structural style. Standard RAG pipelines flatten this variability into plain text, which causes structural loss, weak retrieval, broken citations, and hallucinated answers.

---

## Why It Matters
This document is the governance contract for all later modules. If the project context is underspecified, downstream extraction, chunking, graph construction, retrieval, and response generation will optimize for convenience instead of evidentiary accuracy.

---

## Inputs
- Product intent for legal Q&A, drafting support, recommendation, and risk analysis.
- Multiformat legal source documents: PDF, scanned PDF, DOCX, HTML, image, spreadsheet-derived exhibits.
- Optional metadata hints: jurisdiction, language, document type, issue date, effective date, version label.
- Non-negotiable principles defined by the project owner.

---

## Outputs
- System vision and scope definition.
- Project-wide terminology.
- Design philosophy and legal AI constraints.
- Accuracy, hallucination, and traceability rules.
- Success criteria used by implementation and evaluation agents.

---

## Core Ideas
### System Vision
The system is a legal document intelligence platform that converts source files into a traceable structured representation, retrieval-ready chunks, and a provenance-preserving legal knowledge graph that supports grounded reasoning.

### Design Philosophy
- Structure-first, not text-first.
- Local-first extraction, AI-assisted only where local methods underperform.
- Long-form plain legal text stays on deterministic local extraction unless specific regions require escalation.
- Table and image regions are treated as precision-critical regions and may use stricter AI-assisted recovery or verification than plain text.
- Provenance-first storage for every extracted unit.
- Retrieval-aware parsing and graph-aware chunking.
- Refusal is preferred over unsupported completion.

### Scope
- Document ingestion and profiling.
- Layout-aware extraction and OCR.
- Canonical internal document schema.
- Chunking for legal retrieval.
- Graph construction and traversal.
- Hybrid retrieval and grounded response generation.
- Observability, benchmarking, and prompt rules for AI-assisted substeps.

### Non-Scope
- Direct legal advice without human review.
- Autonomous filing, submission, or regulatory action.
- Guarantee of jurisdictional completeness.
- Source document correction beyond mechanical cleanup.
- Rewriting source text into simplified language during extraction.

### Terminology
| Term | Definition |
| --- | --- |
| Document | A single uploaded source file plus derived metadata and processing artifacts. |
| Page | A renderable unit of a source document with page index and layout regions. |
| Region | A page area classified as text, table, image, or mixed content. |
| Block | The smallest canonical extracted content unit with source anchors. |
| Section | A hierarchical structural unit above article or clause where applicable. |
| Article | A numbered legal unit such as article, section, regulation item, or equivalent. |
| Clause | A subordinate legal unit under an article, section, paragraph, or list item. |
| Chunk | A retrieval unit derived from one or more structurally related blocks. |
| Entity | A person, organization, jurisdiction, concept, obligation, citation, or defined term extracted from content. |
| Provenance | The source trace that links derived data back to file, page, region, and text offsets. |
| Confidence | A bounded score representing extraction, classification, linking, or answer support reliability. |

### Legal AI Constraints
- The system may assist legal work; it does not replace legal review.
- Every answer must be grounded in retrieved source evidence or explicitly refused.
- Jurisdiction context is mandatory when legal meaning depends on locale.
- Conflicting authorities must remain visible; they must not be merged into a single synthetic rule.

### Accuracy and Hallucination Rules
- Extraction must preserve source wording except for reversible OCR cleanup.
- Missing source text must remain missing; no inferred filler text is allowed.
- Downstream reasoning may explain retrieved text, but may not claim unseen clauses, tables, or citations.
- Low-confidence artifacts must be marked and optionally excluded from answer generation.
- Parser noise such as duplicated lines, broken headers, orphan footers, or garbage OCR fragments must be detected, logged, and suppressed from authoritative retrieval views.

### Success Criteria
- Source-faithful extraction with preserved hierarchy and page traceability.
- Optimal routing by document shape: simple and long-form text local-first, complex table or image regions selectively AI-assisted.
- Chunk boundaries that keep legal meaning intact.
- Retrieval that returns the right clause, article, table, or cited passage.
- Graph relations that preserve hierarchy, citation, and dependency semantics.
- Answers that cite evidence, expose uncertainty, and avoid unsupported claims.

---

## Pipeline
1. Accept file and metadata hints.
2. Profile file type, text layer, scan quality, and layout complexity.
3. Route each region through local or AI-assisted extraction based on evidence.
4. Convert output into the canonical document schema with provenance and confidence.
5. Validate structural integrity and extraction coverage.
6. Chunk content for retrieval without breaking legal meaning.
7. Build graph nodes and edges from structure, entities, and citations.
8. Index chunks, metadata, keywords, and graph access paths.
9. Route user queries to the appropriate retrieval strategy.
10. Generate answers only from retrieved evidence with citations and refusal controls.

---

## Rules
### ALWAYS
- Preserve original wording, numbering, and hierarchy when present.
- Keep page references, source offsets, and file identifiers for every derived unit.
- Prefer deterministic local methods before AI-assisted recovery.
- Keep long textual bodies on local extraction when fidelity is already high.
- Treat tables, citations, definitions, and amendments as first-class legal structures.
- Record confidence and provenance at every stage.

### NEVER
- Invent legal text, citations, or missing rows or cells.
- Summarize during extraction.
- Flatten hierarchical documents into arbitrary token windows.
- Let AI rewrite ambiguous source text without keeping the original.
- Return uncited legal claims as authoritative output.

---

## Decision Logic
- If source content and model output disagree, the source content wins.
- If structure exists in the file, preserve it even when retrieval chunk size becomes uneven.
- If a long document is mostly plain text but contains sparse tables or images, keep the main body local and escalate only the detected complex regions.
- If jurisdiction is unknown, retain neutral extraction and require jurisdiction disambiguation at answer time.
- If extraction confidence is below threshold and recovery fails, mark the segment incomplete and exclude it from authoritative answering.
- If multiple document versions conflict, keep separate version identities and require version-aware retrieval.

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Bilingual or multilingual document | Preserve each language variant as separate blocks with linkage; do not merge translations into one block. |
| Redacted text | Preserve redaction markers and mark missing content explicitly. |
| Heavily scanned appendix | OCR locally first, escalate only low-confidence regions, keep page anchors. |
| Amendment text referencing prior law | Preserve both the amendment clause and outgoing citation links; do not inline the amended text unless explicitly present. |
| Forms with checkboxes and stamps | Treat non-text visual marks as evidence-bearing regions, not noise. |
| Duplicate uploads of same law version | Deduplicate by source hash while keeping separate ingestion events. |

---

## Data Model
High-level project contracts:

```text
Source Document
  -> Profile Artifact
  -> Extraction Artifact
  -> Canonical Structured Document
  -> Chunk Set
  -> Graph Subgraph
  -> Retrieval Evidence Set
  -> Answer Package
```

Each artifact must carry:
- `document_id`
- `source_hash`
- `processing_version`
- `provenance`
- `confidence`
- `status`

---

## Retrieval Impact
Project context constrains retrieval quality by forcing structure preservation, version awareness, jurisdiction awareness, and evidence-first ranking. Without these rules, retrieval favors lexical similarity over legal relevance.

---

## GraphRAG Impact
The graph layer depends on this document for node identity, provenance expectations, confidence semantics, and the rule that hierarchy and citations are more reliable than freeform inferred relations.

---

## Logging
Always log:
- Input metadata hints and detected metadata.
- Strategy decisions for local vs AI-assisted extraction.
- Confidence thresholds used in exclusion or refusal decisions.
- Version and jurisdiction assumptions.
- Any unsupported-answer refusal trigger.

---

## Validation
- Check that each downstream spec preserves the same terminology.
- Check that every processing stage emits provenance and confidence.
- Check that no module allows unsupported generation from incomplete evidence.
- Check that non-scope features do not silently appear in implementation plans.

---

## Future Improvements
- Policy packs for jurisdiction-specific hierarchy grammars.
- Formal legal ontology extensions per domain.
- Human review workflows for disputed or low-confidence authority.
- Temporal reasoning rules for effective dates and amendments.
