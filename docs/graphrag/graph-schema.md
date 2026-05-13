# Graph Schema

## Goal
Define the canonical graph model used to represent legal document structure, citations, entities, and legally meaningful relations for GraphRAG.

---

## Problem
Legal reasoning needs more than embeddings. It needs explicit links between articles, clauses, definitions, amendments, tables, and cited authorities. Without a schema, graph construction becomes inconsistent and unsafe.

---

## Why It Matters
The graph schema governs what can be traversed, cited, compared, and expanded during retrieval. A weak schema causes noisy expansion and unsupported relation claims.

---

## Inputs
- Canonical structured document objects.
- Chunk metadata and provenance.
- Entity extraction and citation parsing outputs.
- Relation extraction outputs with confidence and evidence.

---

## Outputs
- Node type definitions.
- Edge type definitions.
- Direction, confidence, and provenance rules.
- Mapping rules from document structure to graph form.

---

## Core Ideas
### Node Types
| Node Type | Purpose |
| --- | --- |
| Document | Root node for an uploaded source file. |
| DocumentVersion | Version-specific node for amended or revised documents. |
| Section | Hierarchy node for chapters, sections, titles, parts, schedules, annexes. |
| Article | Operative legal unit at article or equivalent level. |
| Clause | Subordinate operative unit including paragraphs, items, points, subclauses. |
| Table | Table object node. |
| TableRow | Row-level node when row retrieval or obligation mapping is needed. |
| ImageEvidence | Visual evidence node for scanned or diagram-based content. |
| Chunk | Retrieval-facing node linked to structure. |
| DefinedTerm | Term explicitly defined in source text. |
| Entity | Party, person, organization, authority, jurisdiction, court, or regulator. |
| LegalConcept | Abstract concept such as confidentiality, termination, penalty, or notice. |
| Citation | Explicit source reference to another provision or document. |
| Obligation | Action or duty extracted from text with supporting evidence. |
| Condition | Precondition or qualifier attached to an obligation or rule. |
| Exception | Exception or carve-out node. |
| Penalty | Consequence or sanction node. |

### Edge Types
| Edge Type | Direction | Meaning |
| --- | --- | --- |
| CONTAINS | parent -> child | Structural hierarchy. |
| PRECEDES | earlier -> later | Source order within the same parent scope. |
| HAS_TABLE | structure -> table | Legal unit contains a table. |
| HAS_IMAGE | structure -> image | Legal unit references or contains visual evidence. |
| DERIVED_TO_CHUNK | source unit -> chunk | Retrieval view derived from a structure node. |
| MENTIONS | source unit -> entity or concept | Surface mention without stronger semantics. |
| DEFINES | clause or article -> defined term | Source defines a term. |
| REFERS_TO | source unit -> source unit | Cross-reference within or across documents. |
| CITES | source unit -> citation | Explicit citation string anchored in text. |
| RESOLVES_TO | citation -> target node | Citation target resolution. |
| APPLIES_TO | rule node -> entity or jurisdiction | Scope of applicability. |
| IMPOSES | clause or table row -> obligation | Duty creation. |
| QUALIFIED_BY | obligation or rule -> condition | Condition or qualifier relation. |
| EXCEPTED_BY | rule or obligation -> exception | Carve-out relation. |
| ENFORCED_BY | rule or obligation -> penalty | Consequence relation. |
| SUPPORTS | evidence node -> claim-like node | Direct evidence support. |
| CONTRADICTS | node -> node | Evidence-backed conflict relation. |
| AMENDS | source unit -> target source unit | Amendment or modification link. |

### Direction Rules
- Hierarchy edges always point from broader to narrower units.
- Order edges always point forward in source order.
- Citation edges point from citing source to citation object, then from citation object to resolved target.
- Support edges point from evidence-bearing nodes to inferred or summarized nodes, never the reverse.

### Confidence Rules
- Structural edges default high confidence if parser validation passes.
- Citation resolution confidence depends on citation parse quality, target uniqueness, and version match.
- Entity and concept mention edges can be medium confidence when based on deterministic matching.
- Semantic relation edges such as `CONTRADICTS` require evidence from at least one explicit source anchor and should default lower than structural edges.

### Provenance Rules
Every node and edge must carry:
- `document_id`
- source anchors to block, page, region, or cell
- extraction or linking method
- confidence
- processing version

### Mapping to Document Structure
- Section, article, clause, table, and image nodes are created directly from canonical document objects.
- Chunk nodes are derived views linked back to structure nodes.
- Citation, obligation, condition, exception, and penalty nodes are created only when explicit textual evidence exists.

---

## Pipeline
1. Receive canonical document and chunk set.
2. Create structural nodes from document hierarchy.
3. Create chunk nodes linked to source structure.
4. Create citation nodes from explicit references.
5. Create entity, concept, defined term, obligation, condition, exception, and penalty nodes where evidence supports them.
6. Create edges according to hierarchy, order, citation, and legal-relation rules.
7. Attach provenance and confidence to each node and edge.
8. Validate schema compliance before indexing.

---

## Rules
### ALWAYS
- Preserve hierarchy as the graph backbone.
- Separate citation strings from resolved citation targets.
- Keep structural, citation, and semantic edge families distinguishable.
- Require provenance for every edge.
- Distinguish explicit textual relations from inferred relations.

### NEVER
- Merge distinct versions of a document into one node without version tracking.
- Create legal-relation edges from unsupported paraphrase.
- Resolve ambiguous citations silently.
- Use chunk nodes as the only representation of structure.
- Assign high confidence to unsupported semantic edges.

---

## Decision Logic
```text
if relation is directly encoded by document hierarchy:
    create structural edge with high confidence
elif relation is an explicit citation:
    create citation node and attempt target resolution
elif relation is extracted from operative legal language with source anchors:
    create semantic edge with bounded confidence
else:
    do not create relation
```

Citation preservation rule:
```text
citing clause -> CITES -> citation node -> RESOLVES_TO -> target clause/article/document
```

This preserves both literal citation text and resolved target identity.

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Ambiguous citation to "Article 5" across multiple laws | Keep citation node unresolved or multi-candidate; do not force one target. |
| Table row implies an obligation | Create row node and attach `IMPOSES` only if row semantics are explicit. |
| OCR-degraded defined term | Create mention only unless definition structure is confidently recovered. |
| Cross-jurisdiction same-named act | Separate by jurisdiction and version; never deduplicate globally by title only. |
| Contradictory clauses in different versions | Use `CONTRADICTS` only with version-aware provenance. |
| Diagram labels cited by clause | Preserve `HAS_IMAGE` and optional `SUPPORTS`; avoid over-interpreting spatial meaning. |

---

## Data Model
`GraphNode` minimum fields:
- `node_id`
- `node_type`
- `label`
- `document_scope`
- `source_trace`
- `confidence`
- `attributes`

`GraphEdge` minimum fields:
- `edge_id`
- `edge_type`
- `from_node_id`
- `to_node_id`
- `confidence`
- `provenance`
- `method`
- `active_version_range`

---

## Retrieval Impact
The graph schema enables retrieval to expand from a matched clause to its parent article, cited authorities, definitions, related table rows, and amendment context without guessing hidden relations.

---

## GraphRAG Impact
This document is the GraphRAG contract itself. It defines which nodes can seed traversal, which edges are safe to expand, and how provenance controls trust during graph-based reasoning.

---

## Logging
Always log:
- node and edge creation counts by type
- unresolved citations
- low-confidence semantic relations
- version conflicts
- provenance completeness failures

---

## Validation
- Validate allowed node and edge types only.
- Validate edge direction rules.
- Validate provenance completeness for all edges.
- Validate confidence ranges by edge family.
- Validate citation resolution against known targets.

---

## Future Improvements
- Richer temporal edges for effective dates and repeals.
- Domain ontologies for contracts, labor law, tax law, and litigation.
- Typed support/contradiction explanations.
- Cross-document precedent or interpretation links where supported.
