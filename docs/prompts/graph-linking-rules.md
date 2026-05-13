# Graph Linking Rules

## Goal
Define the prompt contract for AI-assisted entity linking, citation linking, contradiction detection, support linking, and legal relation extraction when deterministic methods are insufficient.

---

## Problem
AI can help resolve ambiguous legal references and relations, but it can also create plausible yet unsupported graph edges that later contaminate GraphRAG retrieval.

---

## Why It Matters
Graph-linking prompts must be evidence-bounded. Every proposed relation must be traceable to explicit source spans and must preserve ambiguity when the evidence is insufficient.

---

## Inputs
- candidate nodes and source spans
- citation strings and candidate targets
- entity mention contexts
- existing graph neighborhood
- allowed relation types and confidence policy

---

## Outputs
- relation proposals
- entity link proposals
- unresolved ambiguity markers
- confidence and evidence notes

---

## Core Ideas
### Allowed AI Actions
- rank candidate citation targets
- link entity mentions when contextual evidence is sufficient
- identify explicit parent-child or reference relations from text
- flag contradiction or support candidates when both supporting spans are present

### Forbidden AI Actions
- invent targets absent from candidates
- create relations without evidence spans
- treat semantic similarity as contradiction proof
- merge entities across jurisdictions or versions without support

### Relation Classes
- parent-child linking
- citation linking
- support linking
- contradiction detection
- obligation-condition-exception linkage

### Confidence Handling
- high confidence only when explicit textual evidence and unique target alignment exist
- medium confidence when evidence is explicit but ambiguity remains bounded
- low confidence proposals should remain unresolved or suppressed

---

## Pipeline
1. Supply candidate nodes, allowed relation types, and source evidence spans.
2. Ask the AI to choose among candidates or return unresolved.
3. Require explicit evidence references for every proposed relation.
4. Validate proposals against schema, provenance, and confidence rules.
5. Accept only supported links and suppress the rest.

---

## Rules
### ALWAYS
- Ask the model to choose from explicit candidate sets where possible.
- Require evidence spans for every link.
- Preserve unresolved state when evidence is ambiguous.
- Keep citation text separate from resolved citation targets.
- Bound relation types to the allowed schema.

### NEVER
- Ask the model open-endedly what a node should connect to.
- Accept relation labels outside the graph schema.
- Use AI-generated world knowledge as linking evidence.
- Convert ambiguous comparison into contradiction without proof.
- Promote low-confidence links into authoritative graph edges.

---

## Decision Logic
```text
if deterministic citation resolution is unique:
    do not call AI
elif candidate targets are few and evidence spans are explicit:
    call AI for target ranking

if relation requires comparing two clauses:
    require evidence spans from both clauses
    if support is insufficient:
        return unresolved

if entity mention is cross-jurisdiction or cross-version ambiguous:
    keep separate nodes unless strong contextual evidence exists
```

Required response shape:

```text
proposals[]
  relation_type
  from_node_id
  to_node_id
  evidence_refs[]
  confidence
  rationale
unresolved[]
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Citation string matches multiple article targets | Return ranked candidates or unresolved; do not force one. |
| Same party name appears in multiple contracts | Use contract scope and role context before linking. |
| Clause appears to contradict another only after paraphrase | Return unresolved unless explicit conflict language exists. |
| Table row supports obligation in clause text | Link only if the row and clause are explicitly aligned. |
| External authority not in corpus | Allow placeholder external target only if explicitly cited. |
| Definition term reused in everyday language | Link to defined term only where contextual usage fits. |

---

## Data Model
`AIGraphLinkRequest` fields:
- `request_id`
- `candidate_nodes`
- `candidate_relations`
- `source_evidence_refs`
- `allowed_relation_types[]`
- `schema_version`

`AIGraphLinkResponse` fields:
- `proposals[]`
- `unresolved[]`
- `confidence_summary`

---

## Retrieval Impact
Strict graph-linking prompts improve retrieval only when they add evidence-backed links. Conservative unresolved handling reduces noisy graph expansion and false relation-based recall.

---

## GraphRAG Impact
These prompt rules directly protect GraphRAG from speculative edges. They ensure graph traversal expands from trustworthy links and preserves ambiguity where the corpus does not resolve it.

---

## Logging
Always log:
- reason for AI linking
- candidate set size
- accepted proposals
- suppressed proposals
- unresolved outputs
- evidence refs used

---

## Validation
- Validate proposal schema conformance.
- Validate all evidence refs exist and map to source artifacts.
- Validate confidence thresholds by relation class.
- Audit accepted contradiction and support edges manually at higher rates.
- Compare AI proposals with deterministic baselines.

---

## Future Improvements
- Better candidate pruning before AI linking.
- Stronger role-aware entity linking.
- Temporal contradiction detection across versions.
- Prompt sets tuned for specific legal relation families.
