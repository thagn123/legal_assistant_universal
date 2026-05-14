# Hybrid Retrieval And GraphRAG

## Goal
Retrieve accurate legal evidence by combining structural, keyword, semantic, metadata, citation, and graph signals.

## Retrieval Modes
| Mode | Use |
| --- | --- |
| Canonical reference search | Exact article/clause lookup across languages. |
| Keyword search | Legal terms, names, phrases, citations. |
| Alias keyword search | Cross-language legal terminology matching. |
| Semantic search | Meaning-based retrieval when embeddings are configured. |
| Metadata filtering | Jurisdiction, language, document type, version. |
| Graph traversal | Retrieve linked definitions, references, dependencies, and context. |

## Current Retrieval Flow
```text
Query
  -> Normalize query
  -> Extract canonical refs
  -> Search canonical refs
  -> Search multilingual aliases
  -> Search raw keywords
  -> Optional semantic search
  -> Score and rerank
```

## GraphRAG Retrieval Flow
```text
Query
  -> Retrieve top chunks/nodes
  -> Select graph seeds
  -> Expand through allowed edges
  -> Assemble evidence bundles
  -> Reason with citations
```

## Scoring Requirements
A retrieval result should score higher when:
- it matches an exact canonical ref
- it matches multiple query terms
- it has strong structural context
- it has citations and source anchors
- it is not degraded

A retrieval result should score lower when:
- it is extremely long and matches weakly
- it is OCR-degraded
- it lacks provenance
- it comes from unresolved or ambiguous structure

## Expansion Rules
Graph expansion may traverse:
- parent section/article context
- child clauses
- cited provisions
- definitions
- attached tables/images
- direct support or contradiction edges when evidence-backed

Graph expansion must stop when:
- confidence is too low
- path length is too high
- context budget is reached
- edge type is not allowed for query intent

