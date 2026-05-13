# Graph Builder

## Goal
Define how the system converts extracted legal documents into graph nodes and edges while preserving structure, provenance, deduplication boundaries, and update safety.

---

## Problem
Graph construction can easily overfit noisy extraction or create duplicate entities and unsupported relations. The builder must therefore be conservative, version-aware, and provenance-driven.

---

## Why It Matters
Graph quality determines whether GraphRAG improves retrieval or amplifies noise. A poorly built graph can make wrong evidence look connected and therefore more credible than it is.

---

## Inputs
- Canonical structured document.
- Chunk set.
- Citation parsing output.
- Entity extraction candidates.
- Optional relation extraction candidates.
- Existing graph state for incremental updates.

---

## Outputs
- Graph nodes and edges.
- entity linking decisions.
- deduplication records.
- graph validation report.
- update delta for existing indexes.

---

## Core Ideas
### Node Creation Rules
- Create structural nodes deterministically from canonical document objects.
- Create chunk nodes from validated retrieval chunks only.
- Create citation nodes only from explicit citation spans.
- Create defined term nodes only when definition patterns are explicit.
- Create obligation, condition, exception, and penalty nodes only from text spans with supporting anchors.

### Edge Creation Rules
- Structural edges come first.
- Citation edges come second.
- Entity and concept mention edges come third.
- Semantic legal-relation edges come last and require stronger evidence rules.

### Deduplication
Deduplicate only within safe identity boundaries:
- same canonical source unit -> merge structural duplicates
- same entity surface form plus normalized type plus jurisdictional context -> candidate link, not automatic merge in all cases
- same citation string does not imply same resolved target without scope resolution

### Entity Linking
Entity linking uses:
- normalized surface form
- alias dictionary
- jurisdiction context
- document type context
- nearby role words
- confidence threshold and ambiguity handling

### Incomplete Extraction Policy
If extraction is incomplete:
- build structural graph from validated content only
- keep unresolved citation or entity nodes separate
- suppress low-support semantic edge creation

### Update Safety
Graph updates are additive and versioned. Replacement is allowed only for superseded derivations from the same source and processing version lineage.

---

## Pipeline
1. Load canonical document, chunk set, and prior graph state.
2. Create or update document and version nodes.
3. Create structural nodes and `CONTAINS` or `PRECEDES` edges.
4. Create chunk nodes and `DERIVED_TO_CHUNK` edges.
5. Parse citations into citation nodes and resolution candidates.
6. Resolve citations to graph targets when unique and supported.
7. Link entities, concepts, defined terms, and legal relation nodes under evidence rules.
8. Deduplicate safe duplicates and preserve ambiguity where unresolved.
9. Validate node and edge schema, provenance, direction, and confidence.
10. Write graph delta and index refresh events.

---

## Rules
### ALWAYS
- Build structure before semantics.
- Carry source anchors from blocks, cells, or image spans into nodes and edges.
- Preserve ambiguity instead of forcing a link.
- Keep graph updates versioned and reversible.
- Downgrade or suppress edges from incomplete extraction.

### NEVER
- Merge entities solely by string equality across jurisdictions.
- Create `CONTRADICTS`, `AMENDS`, or `SUPPORTS` without explicit evidence.
- Delete prior graph history without lineage tracking.
- Reuse low-confidence OCR text as a basis for strong semantic edges.
- Create graph facts from prompt-generated content that lacks source anchors.

---

## Decision Logic
```text
for each canonical object:
    create deterministic structural node

for each citation span:
    create citation node
    if target resolution is unique and version-compatible:
        create RESOLVES_TO
    else:
        keep unresolved

for each entity candidate:
    if ambiguity <= threshold and provenance is complete:
        link to existing entity or create new node
    else:
        create local unresolved node

for each semantic relation candidate:
    if evidence span exists and confidence >= relation_threshold:
        create relation edge
    else:
        suppress
```

Update rule:
```text
if same document_id and new processing_version replaces prior derived artifacts:
    mark prior derivations inactive
    keep lineage
else:
    append as new graph material
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Two identical party names in different roles | Keep separate nodes unless role and context support merge. |
| Citation refers to repealed provision | Link to target version node and mark temporal status if known. |
| Table row mentions a party absent elsewhere | Create row-scoped entity mention with limited confidence. |
| OCR breaks article numbering | Preserve structural graph from validated numbering only; keep unresolved fragments local. |
| Re-upload of same file with improved extraction | Update derived nodes by lineage, not by deleting history. |
| Clause references external law not in corpus | Preserve citation node unresolved to internal target; optionally link to external placeholder document. |

---

## Data Model
`GraphBuildJob` fields:
- `job_id`
- `document_id`
- `processing_version`
- `input_artifact_ids`
- `created_nodes`
- `created_edges`
- `dedup_actions`
- `unresolved_items`
- `validation_status`

---

## Retrieval Impact
Well-built graphs improve recall for cross-references, definitions, amendment chains, and related obligations. Conservative suppression of weak edges reduces noisy expansion during retrieval.

---

## GraphRAG Impact
This builder determines whether GraphRAG uses a trustworthy evidence graph or a speculative semantic web. Provenance-bearing structural and citation edges should dominate traversal paths.

---

## Logging
Always log:
- node and edge counts by type
- entity link confidence and ambiguity
- unresolved citation counts
- suppressed relation counts
- graph lineage updates
- validation failures

---

## Validation
- Validate structural coverage against canonical document hierarchy.
- Validate no orphan nodes remain unintentionally.
- Validate deduplication decisions against identity boundaries.
- Validate unresolved items are explicitly marked.
- Regression-test graph deltas on amended document versions.

---

## Future Improvements
- Better cross-document entity resolution with legal role ontologies.
- Temporal graph overlays for amendments and effective dates.
- Human review queues for ambiguous high-value links.
- Selective relation extraction tuned by query workload.
