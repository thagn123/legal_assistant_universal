# Hybrid Retrieval

## Goal
Define the retrieval architecture that combines vector search, keyword search, metadata filters, citation-aware retrieval, and graph expansion to produce evidence sets for legal reasoning.

---

## Problem
No single retrieval method is sufficient for legal work. Vector search improves semantic recall, keyword search catches exact citations and terms, metadata filters constrain scope, and graph traversal supplies context not present in isolated chunks.

---

## Why It Matters
Retrieval quality is the main control surface for hallucination prevention. If the right evidence is not retrieved, even a careful reasoning layer will either refuse too often or answer from incomplete support.

---

## Inputs
- User query and query classification.
- Chunk index with embeddings.
- Keyword index.
- Metadata store.
- Graph store and traversal policy.
- Retrieval thresholds and reranking settings.

---

## Outputs
- `RetrievalPlan`
- ranked `EvidenceSet`
- citation coverage summary
- retrieval warnings and fallback flags

---

## Core Ideas
### Retrieval Components
| Component | Primary Strength |
| --- | --- |
| Vector search | Semantic similarity and paraphrase tolerance. |
| Keyword search | Exact terms, article numbers, definitions, and citation strings. |
| Metadata filtering | Jurisdiction, document type, language, version, date, and source scoping. |
| Graph retrieval | Structural, citation, and relation-aware expansion. |
| Reranking | Evidence ordering by legal relevance and support quality. |

### Hybrid Strategy
Hybrid retrieval is layered:
1. scope reduction through metadata
2. parallel vector and keyword retrieval
3. merge and deduplicate candidates
4. optional graph expansion from top seeds
5. reranking against query intent and support completeness

### Citation-Aware Retrieval
Citation-aware behavior includes:
- direct citation string matching
- article and clause number normalization
- citation target resolution using graph mappings
- version-aware disambiguation

### Reranking Factors
- semantic relevance
- exact citation hit
- structure match quality
- query-intent compatibility
- jurisdiction and version match
- provenance completeness
- confidence and degradation penalties

---

## Pipeline
1. Receive query and routing decision.
2. Apply hard metadata filters where known.
3. Execute vector retrieval and keyword retrieval in parallel.
4. Normalize citations, document titles, section numbers, and aliases.
5. Merge and deduplicate candidates by chunk and structural identity.
6. Select top seeds for graph expansion when enabled.
7. Expand through allowed graph paths.
8. Rerank the merged evidence set.
9. Validate support sufficiency and citation coverage.
10. Return ranked evidence bundles with retrieval diagnostics.

---

## Rules
### ALWAYS
- Use metadata constraints when jurisdiction, document family, or version is known.
- Preserve the origin of each candidate: vector, keyword, graph, or combined.
- Rerank with legal structure and citation features, not embedding score alone.
- Keep degraded or low-confidence evidence visible to the reasoner.
- Support fallback retrieval when primary methods underperform.

### NEVER
- Let graph expansion replace first-pass retrieval.
- Ignore exact article or clause matches when present.
- Mix superseded and active versions without explicit handling.
- Hide retrieval gaps from the response layer.
- Treat dense semantic similarity as proof of legal applicability.

---

## Decision Logic
```text
if query includes explicit citation or numbering:
    prioritize keyword and citation-aware retrieval
elif query is conceptual but scoped to known jurisdiction or document family:
    use hybrid retrieval with metadata filters
else:
    use vector + keyword baseline, then expand selectively

if first-pass evidence lacks structural completeness:
    trigger graph expansion

if no sufficient evidence after reranking:
    fallback to broader metadata scope or lower-threshold keyword retrieval
```

Fallback retrieval order:
1. relax chunk score threshold
2. broaden metadata filters within safe bounds
3. expand query aliases or multilingual variants
4. search parent structure nodes and table projections
5. return insufficient-evidence status if support remains weak

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Query uses article number only | Normalize numbering and search structure-aware indexes before semantic retrieval. |
| Multilingual query against monolingual corpus | Translate or map query terms for retrieval only; preserve original source output language metadata. |
| Table value lookup | Search table row projections and header terms, not prose chunks only. |
| Broad risk query across many contracts | Filter by document family and clause types before expansion. |
| Citation resolves to missing document in corpus | Return local evidence plus explicit unresolved external citation warning. |
| Sparse OCR corpus | Penalize low-confidence evidence and increase exact-keyword reliance. |

---

## Data Model
`RetrievalPlan` fields:
- `query_id`
- `query_class`
- `metadata_filters`
- `retrieval_modes[]`
- `graph_expansion_enabled`
- `reranker_profile`
- `fallback_policy`

`EvidenceItem` fields:
- `evidence_id`
- `chunk_id or node_id`
- `origin_modes[]`
- `score`
- `citations[]`
- `structure_path`
- `confidence`
- `degraded`

---

## Retrieval Impact
This document is the retrieval contract. It balances precision and recall by combining complementary retrieval methods and forcing explicit fallbacks instead of hidden behavior changes.

---

## GraphRAG Impact
Graph retrieval is a controlled augmentation step. Hybrid retrieval seeds the graph with strong first-pass evidence, and graph expansion returns structured neighborhood context rather than replacing retrieval with free exploration.

---

## Logging
Always log:
- applied filters
- candidate counts per retrieval mode
- merge and dedup statistics
- graph expansion usage
- reranking feature summary
- fallback activation and reason

---

## Validation
- Benchmark retrieval separately for citation, clause, table, and conceptual queries.
- Validate filter correctness and version safety.
- Validate graph expansion contribution to answer support.
- Validate failure handling when evidence is insufficient.
- Track recall, precision, and support completeness by query class.

---

## Future Improvements
- Learned hybrid weighting by query class.
- Better multilingual legal term normalization.
- Retrieval-time temporal validity filters.
- Cross-encoder rerankers tuned for legal clause support.
