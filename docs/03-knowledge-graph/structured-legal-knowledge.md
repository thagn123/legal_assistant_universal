# Structured Legal Knowledge

## Goal
Transform extracted content into structured legal knowledge and graph-ready objects.

## Core Representation
The system must not store only raw text. It must build:
- document metadata
- pages
- blocks
- sections
- articles
- clauses
- tables
- images
- chunks
- graph nodes
- graph edges

## Legal Knowledge Graph
The graph represents legal structure and relationships.

Node types:
- `Document`
- `Section`
- `Article`
- `Clause`
- `Table`
- `ImageEvidence`
- `Chunk`
- `Entity`
- `LegalConcept`
- `Citation`
- `Obligation`
- `Condition`
- `Exception`
- `Penalty`

Edge types:
- `CONTAINS`
- `PRECEDES`
- `HAS_TABLE`
- `HAS_IMAGE`
- `DERIVED_TO_CHUNK`
- `CITES`
- `REFERS_TO`
- `RESOLVES_TO`
- `SUPPORTS`
- `CONTRADICTS`
- `DEPENDS_ON` as implementation-specific semantic relation if added explicitly
- `ALIAS_OF` for multilingual equivalents

## Canonical References
Canonical references normalize cross-language legal structure.

Examples:
```text
Article 1 -> article_1
Art. 1 -> article_1
Dieu 1 -> article_1
Clause 3(a) -> clause_3_a
```

Required behavior:
- attach canonical refs to structured chunks
- use canonical refs for retrieval and alias edges
- never use canonical refs as proof of legal equivalence without source evidence

## Multilingual Graph Aliasing
`ALIAS_OF` edges connect structurally compatible nodes that share canonical refs.

Rules:
- alias structure nodes only
- do not alias `Chunk` nodes
- keep alias edges provenance-bound
- create symmetric alias edges only when intended by graph policy

## Semantic Relations
Semantic legal relations include:
- obligation
- prohibition
- right
- penalty
- condition
- responsibility
- dependency
- contradiction
- support

These relations require explicit evidence. Do not create them from similarity alone.

