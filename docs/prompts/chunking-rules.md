# Chunking Rules

## Goal
Define the prompt contract for AI-assisted chunking when deterministic chunk boundaries are insufficient or when semantic boundary hints are needed for weakly structured legal text.

---

## Problem
AI can help identify semantic boundaries in weakly structured documents, but it may also over-split or merge content in ways that distort legal meaning.

---

## Why It Matters
Chunking prompts must preserve legal semantics, hierarchy, citations, and table dependencies. If the prompt is weak, retrieval quality degrades and GraphRAG seeds become noisy.

---

## Inputs
- canonical ordered blocks
- structure hints
- token budget
- table and image references
- chunking strategy target

---

## Outputs
- chunk proposals
- boundary rationale
- overlap recommendations
- uncertainty or fallback flags

---

## Core Ideas
### Allowed AI Actions
- suggest semantic boundaries when explicit hierarchy is weak
- identify clause-introduction and exception dependencies
- recommend header carryover for split sections
- group mixed evidence units when structure alone is insufficient

### Forbidden AI Actions
- rewrite source text
- drop numbering, citations, or table dependencies
- merge unrelated provisions for token convenience
- split legal conditions from outcomes without justification

### Context Preservation Rules
- include parent heading context when needed
- keep definitions with their defined terms
- keep table headers with dependent rows
- keep exceptions and penalties linked to the base rule

### Output Schema
AI output must describe chunk boundaries as references to existing blocks, not regenerated text only.

---

## Pipeline
1. Supply ordered block list and structure hints.
2. Specify target strategy and token budget.
3. Ask the AI to propose block-group boundaries only.
4. Validate that proposed boundaries respect prohibited split rules.
5. Accept, adjust, or reject proposals based on deterministic validators.

---

## Rules
### ALWAYS
- Ask the model to operate on block identifiers and structure paths.
- Require boundary rationale in legal terms.
- Require explicit handling of tables, definitions, and exceptions.
- Validate proposals against token and structure constraints.
- Keep deterministic validation as the final authority.

### NEVER
- Ask the model to produce final chunk text without block references.
- Let the model invent missing hierarchy.
- Accept a split that separates dependent legal meaning.
- Use AI chunking when deterministic structural chunking already works.
- Treat boundary rationale as proof without validation.

---

## Decision Logic
```text
if structure is reliable:
    do not call AI for chunking
elif document is weakly structured but text quality is acceptable:
    call AI for boundary suggestion
elif OCR quality is low:
    avoid AI fine-grained chunking and use conservative fallback
if tables or mixed evidence units are present:
    require explicit sibling or grouped chunk recommendations
```

Required response shape:

```text
chunks[]
  chunk_ref
  block_refs[]
  structure_path
  overlap_from[]
  rationale
  warnings[]
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Long unnumbered prose with visible topic shifts | Suggest semantic boundaries but keep related obligations together. |
| Dense list of exceptions | Keep under the governing clause introduction. |
| Table preceded by short explanatory sentence | Recommend grouped or sibling chunking, not isolated table-only retrieval unless safe. |
| Annex with weak headings | Use semantic grouping plus annex-level parent context. |
| Mixed-language aligned clauses | Keep separate language block groups and link equivalence externally. |
| Low-confidence OCR paragraphs | Return conservative large chunks with warnings. |

---

## Data Model
`AIChunkingRequest` fields:
- `request_id`
- `document_id`
- `target_strategy`
- `block_sequence`
- `token_budget`
- `constraints[]`

`AIChunkingResponse` fields:
- `chunk_proposals[]`
- `boundary_warnings[]`
- `confidence`

---

## Retrieval Impact
Strict chunking prompts improve retrieval when structure is weak by adding semantic sensitivity without sacrificing legal integrity. They should increase recall only when deterministic chunking cannot do so safely.

---

## GraphRAG Impact
Chunk proposals influence graph seed quality. Boundary rules that preserve legal dependencies lead to cleaner structural and citation expansion paths.

---

## Logging
Always log:
- reason for AI chunking
- proposed boundaries
- rejected proposals
- validation failures
- final accepted boundaries
- confidence and warnings

---

## Validation
- Validate proposals against prohibited split rules.
- Validate all block references exist and remain ordered.
- Validate token budgets after deterministic rendering.
- Validate table and header dependencies.
- Review retrieval performance gains before broad adoption.

---

## Future Improvements
- Better prompts for weakly structured annexes.
- Query-intent-conditioned alternate chunk views.
- Multi-pass boundary suggestion with deterministic pruning.
- Language-specific semantic boundary packs.
