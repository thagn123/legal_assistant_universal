# Document Schema

## Goal
Define the canonical internal representation for extracted legal documents, including structure, provenance, confidence, and traceability fields required by chunking, retrieval, and GraphRAG.

---

## Problem
If each module invents its own intermediate format, structure gets lost, confidence becomes inconsistent, and provenance breaks across ingestion, chunking, and graph construction.

---

## Why It Matters
The schema is the system handoff contract. It must be stable, explicit, and sufficiently rich to preserve evidence without forcing downstream modules to reinterpret raw extraction output.

---

## Inputs
- validated extraction output from text, table, and image pipelines
- document profile metadata
- layout analysis results
- OCR, repair, and normalization diagnostics

---

## Outputs
- canonical `Document` object
- supporting `Page`, `Block`, `Table`, `Image`, `Section`, `Article`, and `Clause` objects
- shared metadata, offsets, confidence, and traceability contracts

---

## Core Ideas
### Schema Principles
- One canonical object model for all document families.
- Raw evidence and cleaned representations must coexist.
- Provenance must survive every transformation.
- Hierarchy is explicit, not inferred downstream.
- Tables and images are first-class objects, not embedded text only.

### Canonical Shape

```text
Document
  metadata
  profile
  pages[]
  sections[]
  articles[]
  clauses[]
  blocks[]
  tables[]
  images[]
  rendered_outputs
  validation
```

### Object Identity
Every object must have:
- a stable unique identifier
- a type or kind
- provenance and confidence
- parent or related object references where applicable

---

## Pipeline
1. Create `Document` root from upload and profile data.
2. Create `Page` objects in physical source order.
3. Create `Block` objects from ordered extracted regions.
4. Create `Table` and `Image` objects as first-class evidence objects.
5. Build `Section`, `Article`, and `Clause` hierarchy from validated structure.
6. Attach shared metadata, offsets, confidence, and traceability fields to every object.
7. Validate referential integrity before chunking and graph build.

---

## Rules
### ALWAYS
- Preserve both raw and normalized text where normalization occurred.
- Use explicit references instead of implicit nesting alone.
- Keep page and region provenance on every evidence-bearing object.
- Allow partial objects when evidence is incomplete, but mark them degraded.
- Version the schema and processing lineage.

### NEVER
- Store cleaned text only when raw extraction differs materially.
- Use untyped freeform metadata bags for core legal structure.
- Drop unreadable or unresolved content without status markers.
- Reassign source anchors during downstream transformation.
- Let chunking or graph modules mutate canonical source content.

---

## Decision Logic
```text
if a structure unit is confidently detected:
    create explicit section/article/clause object
else:
    preserve content as blocks and keep structure unresolved

if a table or image carries legal evidence:
    create first-class table or image object

if normalization changes visible source form:
    keep raw and clean variants side by side
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Document lacks explicit hierarchy | Keep blocks and unresolved structure groups without inventing articles or clauses. |
| Table spans multiple pages | Store one logical table with multiple page refs and continuation metadata. |
| Bilingual contract | Preserve language-specific blocks and cross-links without merging text. |
| OCR-repaired scan | Keep raw OCR, cleaned OCR, repair status, and confidence. |
| Annex attached to main law | Represent annex as section-like structure with its own children. |
| Image-only signature page | Create image object and related block only if text is extracted. |

---

## Data Model
### Shared Supporting Types

#### Metadata
| Field | Type | Description |
| --- | --- | --- |
| `title` | string | Best-known document title from source or metadata. |
| `document_family` | string | Broad class such as statute, contract, regulation, judgment, annex, form. |
| `document_type` | string | More specific type label used for retrieval filters. |
| `jurisdiction` | string | Country or primary legal domain. |
| `subjurisdiction` | string or null | State, province, court, agency, or other narrower scope. |
| `languages` | string[] | Language codes detected or supplied. |
| `version_label` | string or null | Version or revision identifier if known. |
| `issued_date` | string or null | Official issue date if present. |
| `effective_date` | string or null | Effective date if present. |
| `authority` | string or null | Issuing authority, court, regulator, or contract source party label. |
| `source_uri` | string or null | External source location if known. |
| `tags` | string[] | Optional non-core labels for indexing or workflow. |

#### SourceOffsets
| Field | Type | Description |
| --- | --- | --- |
| `extraction_stream_id` | string | Identifier of the raw extraction stream being referenced. |
| `page_id` | string | Page containing the source span. |
| `region_id` | string or null | Region containing the source span when available. |
| `char_start` | integer or null | Inclusive character offset within the extraction stream. |
| `char_end` | integer or null | Exclusive character offset within the extraction stream. |
| `bbox` | object or null | Bounding box of the span in page coordinates. |
| `line_refs` | string[] | Optional line or segment identifiers within the page. |
| `cell_ref` | string or null | Optional table cell identifier if the span came from a cell. |

#### Confidence
| Field | Type | Description |
| --- | --- | --- |
| `overall` | number | Overall confidence in the object as represented. |
| `extraction` | number or null | Confidence in text extraction fidelity. |
| `structure` | number or null | Confidence in hierarchy placement. |
| `ocr` | number or null | Confidence in OCR text, when applicable. |
| `topology` | number or null | Confidence in table topology, when applicable. |
| `linkage` | number or null | Confidence in reference linkage, when applicable. |
| `degraded` | boolean | True when the object is present but not fully trustworthy. |
| `reasons` | string[] | Reason codes explaining low confidence or degradation. |

#### Traceability
| Field | Type | Description |
| --- | --- | --- |
| `trace_id` | string | End-to-end trace identifier from processing pipeline. |
| `source_hash` | string | Hash of the original source file. |
| `extractor` | string | Primary tool or model that created the object. |
| `extractor_version` | string | Version of the extractor or prompt set. |
| `repair_methods` | string[] | Cleanup or repair methods applied to reach the current object. |
| `derived_from_refs` | string[] | Parent artifact identifiers used to derive the object. |
| `processing_version` | string | Pipeline version used to create the object. |
| `created_at` | string | Creation timestamp. |

#### RegionRef
| Field | Type | Description |
| --- | --- | --- |
| `region_id` | string | Unique page region identifier. |
| `type` | string | `text`, `table`, `image`, or `mixed`. |
| `bbox` | object | Region bounding box. |
| `reading_order_index` | integer | Region order within the page. |
| `confidence` | number | Region classification confidence. |

### Document Object
| Field | Type | Description |
| --- | --- | --- |
| `document_id` | string | Stable document identifier. |
| `schema_version` | string | Canonical schema version. |
| `source_filename` | string | Original filename. |
| `mime_type` | string | Original MIME type. |
| `file_type` | string | Normalized file type such as `pdf`, `docx`, `image`, `html`. |
| `metadata` | Metadata | Canonical metadata object. |
| `profile` | object | Profile summary used for routing and validation. |
| `pages` | Page[] | Physical pages in source order. |
| `sections` | Section[] | Section-like structural units. |
| `articles` | Article[] | Article-level structural units. |
| `clauses` | Clause[] | Clause-level structural units. |
| `blocks` | Block[] | Ordered extracted text blocks. |
| `tables` | Table[] | Table evidence objects. |
| `images` | Image[] | Image evidence objects. |
| `rendered_outputs` | object | Derived `html` and `markdown` representations. |
| `validation` | object | Validation summary, unresolved issues, and coverage metrics. |
| `confidence` | Confidence | Document-level confidence summary. |
| `traceability` | Traceability | Document-level provenance and processing lineage. |

### Page Object
| Field | Type | Description |
| --- | --- | --- |
| `page_id` | string | Stable page identifier. |
| `page_index` | integer | One-based physical page order in the source file. |
| `printed_page_label` | string or null | Human-visible page number if different from physical order. |
| `width` | number | Page width in normalized coordinates or source units. |
| `height` | number | Page height in normalized coordinates or source units. |
| `rotation` | integer | Rotation in degrees after normalization. |
| `text_layer_available` | boolean | Whether usable extractable text existed on the page. |
| `ocr_applied` | boolean | Whether OCR was run on the page or page regions. |
| `layout_irregularity_score` | number | Page-level layout complexity signal. |
| `regions` | RegionRef[] | Ordered page regions. |
| `block_ids` | string[] | Blocks originating from this page. |
| `table_ids` | string[] | Tables originating from this page. |
| `image_ids` | string[] | Images originating from this page. |
| `confidence` | Confidence | Page-level confidence summary. |
| `traceability` | Traceability | Page-level provenance lineage. |

### Block Object
| Field | Type | Description |
| --- | --- | --- |
| `block_id` | string | Stable block identifier. |
| `page_id` | string | Owning page identifier. |
| `region_id` | string | Source region identifier. |
| `block_type` | string | `heading`, `paragraph`, `list_item`, `footnote`, `citation`, `caption`, `table_ref`, or similar. |
| `order_index` | integer | Global order within the document or within the page according to implementation choice; must be consistent. |
| `raw_text` | string | Direct source-faithful extraction. |
| `clean_text` | string | Mechanically normalized text; empty only if identical behavior is defined elsewhere. |
| `html_fragment` | string or null | Optional canonical HTML fragment. |
| `markdown_fragment` | string or null | Optional canonical Markdown fragment. |
| `language` | string or null | Dominant language of the block if known. |
| `parent_structure_id` | string or null | Closest section, article, or clause container. |
| `citations` | string[] | Citation span identifiers or citation strings detected in the block. |
| `source_offsets` | SourceOffsets[] | Source span anchors for the block text. |
| `bbox_refs` | object[] | Bounding boxes when multiple fragments compose one block. |
| `confidence` | Confidence | Block-level confidence summary. |
| `traceability` | Traceability | Block-level provenance lineage. |

### Table Object
| Field | Type | Description |
| --- | --- | --- |
| `table_id` | string | Stable table identifier. |
| `title` | string or null | Table title or caption when present. |
| `page_refs` | string[] | Pages contributing to the table. |
| `bbox_refs` | object[] | Bounding boxes across contributing pages. |
| `related_structure_id` | string or null | Owning section, article, or clause when attached. |
| `row_count` | integer | Number of logical rows. |
| `column_count` | integer | Number of logical columns. |
| `headers` | object[] | Header row or column definitions. |
| `rows` | object[] | Ordered logical rows. |
| `cells` | object[] | Cell-level objects with row, column, span, and text fields. |
| `merged_ranges` | object[] | Explicit merged-cell coordinates. |
| `continuation` | object or null | Multi-page continuation metadata. |
| `html` | string or null | HTML rendering when representable. |
| `markdown` | string or null | Markdown rendering when safe. |
| `projection_text` | string | Retrieval-oriented table-to-text projection. |
| `confidence` | Confidence | Table content and topology confidence. |
| `traceability` | Traceability | Table-level provenance lineage. |

### Image Object
| Field | Type | Description |
| --- | --- | --- |
| `image_id` | string | Stable image identifier. |
| `page_id` | string | Owning page identifier. |
| `bbox` | object | Bounding box of the image region. |
| `image_class` | string | `scan_text`, `seal`, `stamp`, `signature`, `diagram`, `photo`, `mixed`, or similar. |
| `raw_ocr_text` | string | Raw OCR output from the image region. |
| `clean_ocr_text` | string | Cleaned OCR output if cleanup succeeded. |
| `text_spans` | object[] | Optional span-level OCR anchors. |
| `ocr_confidence` | number or null | OCR confidence for image-derived text. |
| `evidence_status` | string | `textual`, `visual_only`, `mixed`, or `unreadable`. |
| `related_structure_ids` | string[] | Linked clauses, articles, or sections when supported. |
| `confidence` | Confidence | Image interpretation confidence summary. |
| `traceability` | Traceability | Image-level provenance lineage. |

### Section Object
| Field | Type | Description |
| --- | --- | --- |
| `section_id` | string | Stable section identifier. |
| `section_kind` | string | `title`, `part`, `chapter`, `section`, `schedule`, `annex`, or equivalent. |
| `label` | string | Source-visible label such as `Chapter II`. |
| `number` | string or null | Extracted numbering token. |
| `title` | string or null | Section heading text. |
| `parent_section_id` | string or null | Parent section if nested. |
| `child_section_ids` | string[] | Nested section children. |
| `article_ids` | string[] | Articles contained by this section. |
| `block_ids` | string[] | Heading or descriptive blocks linked to the section. |
| `page_refs` | string[] | Pages touched by the section. |
| `source_offsets` | SourceOffsets[] | Source spans for section heading or boundaries. |
| `confidence` | Confidence | Section detection confidence. |
| `traceability` | Traceability | Section provenance lineage. |

### Article Object
| Field | Type | Description |
| --- | --- | --- |
| `article_id` | string | Stable article identifier. |
| `label` | string | Source-visible label such as `Article 12` or equivalent. |
| `number` | string or null | Extracted article number token. |
| `title` | string or null | Article heading or rubric. |
| `parent_section_id` | string or null | Owning section. |
| `clause_ids` | string[] | Clauses directly contained by the article. |
| `block_ids` | string[] | Blocks composing the article. |
| `table_ids` | string[] | Tables attached to the article. |
| `image_ids` | string[] | Images attached to the article. |
| `citations` | string[] | Citations explicitly present in the article. |
| `page_refs` | string[] | Pages touched by the article. |
| `source_offsets` | SourceOffsets[] | Source spans for article heading and body. |
| `confidence` | Confidence | Article detection confidence. |
| `traceability` | Traceability | Article provenance lineage. |

### Clause Object
| Field | Type | Description |
| --- | --- | --- |
| `clause_id` | string | Stable clause identifier. |
| `label` | string | Source-visible label such as `1.` or `(a)`. |
| `number` | string or null | Parsed clause numbering token. |
| `clause_kind` | string | `paragraph`, `subclause`, `item`, `point`, `definition`, `exception`, or equivalent. |
| `title` | string or null | Optional clause title when present. |
| `parent_article_id` | string or null | Owning article if applicable. |
| `parent_clause_id` | string or null | Parent clause for nested clause structures. |
| `child_clause_ids` | string[] | Nested subordinate clauses. |
| `block_ids` | string[] | Blocks composing the clause. |
| `table_ids` | string[] | Tables attached to the clause. |
| `image_ids` | string[] | Images attached to the clause. |
| `citations` | string[] | Citations explicitly present in the clause. |
| `defined_terms` | string[] | Defined terms created or used explicitly in the clause when available. |
| `page_refs` | string[] | Pages touched by the clause. |
| `source_offsets` | SourceOffsets[] | Source spans for clause content. |
| `confidence` | Confidence | Clause detection confidence. |
| `traceability` | Traceability | Clause provenance lineage. |

### Rendered Outputs
| Field | Type | Description |
| --- | --- | --- |
| `html` | string or null | Canonical HTML rendering of the document. |
| `markdown` | string or null | Canonical Markdown rendering of the document. |
| `generation_status` | string | Indicates whether each rendering is complete, partial, or unavailable. |

### Validation Summary
| Field | Type | Description |
| --- | --- | --- |
| `coverage_score` | number | Estimated source coverage. |
| `unresolved_issues` | string[] | Outstanding extraction or structure problems. |
| `warnings` | string[] | Non-fatal issues. |
| `validated_at` | string | Validation timestamp. |

---

## Retrieval Impact
This schema gives retrieval explicit units for clauses, tables, citations, and page anchors. That enables scope-aware search, citation-aware ranking, and selective suppression of degraded evidence.

---

## GraphRAG Impact
The graph builder depends on this schema to create stable nodes from structure and evidence objects. Explicit provenance, confidence, and parent-child links reduce graph ambiguity and improve traversal safety.

---

## Logging
Always log:
- schema version
- object counts by type
- unresolved structure rates
- degraded object counts
- missing provenance violations
- referential integrity failures

---

## Validation
- Validate all required identifiers.
- Validate referential integrity across parent and child references.
- Validate that every evidence-bearing object has provenance and confidence.
- Validate that raw and cleaned text are both preserved where they differ.
- Validate page order, block order, and structure order consistency.

---

## Future Improvements
- Formal JSON Schema or typed interface generation.
- Shared ontology field packs for specific legal domains.
- Temporal validity fields for amendment-aware reasoning.
- Alignment objects for multilingual clause equivalence.
