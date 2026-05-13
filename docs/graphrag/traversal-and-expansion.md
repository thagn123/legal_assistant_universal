# Traversal and Expansion

## Goal
Define how GraphRAG traverses and expands from initial retrieval seeds to gather context while limiting noise, preserving legal meaning, and maintaining citation safety.

---

## Problem
Unbounded graph expansion pulls in loosely related content and increases hallucination risk. Legal retrieval requires focused expansion through structure, citations, definitions, and directly relevant obligations.

---

## Why It Matters
Traversal determines whether the system retrieves the right neighborhood around a clause or wanders into tangential material. Good expansion improves completeness; bad expansion fabricates relevance.

---

## Inputs
- Query classification result.
- Initial seed nodes from vector, keyword, metadata, or citation retrieval.
- Graph schema, node metadata, and edge confidence.
- Context budget and traversal policy thresholds.

---

## Outputs
- `TraversalPlan`
- ranked `ExpandedEvidenceSet`
- explanation paths
- stop reasons

---

## Core Ideas
### Traversal Priorities
Legal traversal prioritizes:
1. parent and child hierarchy needed for interpretation
2. explicit citations and resolved targets
3. definitions referenced by matched clauses
4. obligations, conditions, exceptions, and penalties directly attached to the seed
5. nearby source-order neighbors when context is incomplete

### Neighborhood Expansion
Expansion is relation-type aware:
- hierarchy edges for context completion
- citation edges for authority chains
- definition edges for term resolution
- support or contradiction edges for conflict analysis
- table or image evidence edges when the seed depends on non-prose evidence

### Relevance Scoring
Expanded node score combines:
- seed retrieval score
- edge-type weight
- path length penalty
- provenance quality
- confidence
- jurisdiction and version match
- query intent compatibility

### Noise Control
Noise is reduced by:
- edge whitelist per query class
- maximum depth per edge family
- maximum degree fan-out
- suppression of low-confidence semantic edges
- context budget by evidence value, not node count only

### Context Preservation
Expansion should return coherent evidence bundles:
- clause with parent article
- row with table header
- cited clause with citing context
- exception with base rule

---

## Pipeline
1. Receive seed nodes and query class.
2. Build query-class-specific traversal policy.
3. Expand first through high-authority edges: hierarchy, citation, definitions.
4. Score candidate neighbors.
5. Expand selectively through legal relation edges if the query class benefits.
6. Add sibling or parent context where necessary for interpretation.
7. Stop when marginal relevance falls below threshold or context budget is reached.
8. Return ranked evidence bundles and explanation paths.

---

## Rules
### ALWAYS
- Start from retrieved evidence seeds, not from the full graph.
- Prefer explicit structural and citation edges over weak semantic edges.
- Carry path provenance for every expanded node.
- Add context only when it improves interpretability or support completeness.
- Stop expansion when confidence or relevance decays.

### NEVER
- Traverse low-confidence contradiction or support edges without need.
- Expand across version boundaries unless the query requests comparison.
- Treat graph adjacency as proof of legal applicability.
- Return expanded nodes without preserving the path that justified them.
- Spend context budget on decorative or weakly related image nodes.

---

## Decision Logic
```text
if query_class in {factual_lookup, clause_search}:
    expand hierarchy and citations first
elif query_class in {drafting, risk_detection}:
    expand definitions, obligations, exceptions, and contradictions
elif query_class == cross_document_comparison:
    allow version-aware and peer-structure expansion

for each candidate neighbor:
    score = seed_score
          + edge_weight
          + provenance_bonus
          + version_match_bonus
          - path_length_penalty
          - noise_penalty

stop if:
    score < expansion_threshold
    or depth > class_depth_limit
    or context_budget exhausted
```

Suggested depth limits:
- hierarchy: shallow to medium
- citations: shallow to medium
- definitions: shallow
- contradiction/support: shallow unless risk analysis

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Clause cites a table row through nearby prose | Expand to table and header row bundle, not the full schedule by default. |
| Query targets a defined term | Expand to the definition clause first, then to immediate usage clauses only if needed. |
| Multiple cited authorities with same article number | Use version and document scope filters before expansion. |
| Cross-document comparison request | Allow controlled peer traversal across matched documents and versions. |
| Seed comes from low-confidence OCR chunk | Restrict expansion depth and downgrade answer authority. |
| High-degree entity node such as regulator name | Cap fan-out aggressively to avoid graph explosion. |

---

## Data Model
`TraversalPlan` fields:
- `query_id`
- `query_class`
- `seed_node_ids[]`
- `allowed_edge_types[]`
- `depth_limits`
- `score_weights`
- `context_budget`
- `stop_conditions[]`

`ExpandedEvidenceSet` fields:
- `node_ids[]`
- `edge_paths[]`
- `bundle_ids[]`
- `rank_scores`
- `support_status`

---

## Retrieval Impact
Traversal improves retrieval completeness by adding the exact adjacent evidence needed for interpretation. Controlled expansion increases answer quality without replacing primary retrieval.

---

## GraphRAG Impact
Traversal is the operational core of GraphRAG. It determines how graph structure augments seed retrieval and how provenance-bearing paths constrain graph-based reasoning.

---

## Logging
Always log:
- seed nodes
- traversal policy
- expanded node and edge counts
- stop reason
- suppressed neighbors
- final evidence bundle scores

---

## Validation
- Validate traversal reproducibility for the same seeds and policy.
- Validate that all expanded nodes are reachable through allowed paths.
- Validate context bundle completeness for tables, citations, and exceptions.
- Benchmark noise rate by query class.
- Inspect failure cases where expansion omitted required parent or cited context.

---

## Future Improvements
- Learned traversal scoring from answer success.
- Better contradiction path explanations.
- Adaptive fan-out control by graph density.
- Temporal traversal policies for superseded law versions.
