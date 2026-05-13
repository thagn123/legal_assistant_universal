# Query Routing

## Goal
Define how user queries are classified and routed to the correct retrieval and reasoning strategy for legal Q&A, clause search, drafting, risk analysis, explanation, and comparison.

---

## Problem
Different legal tasks require different evidence shapes. A clause lookup wants exact citation retrieval; drafting support wants similar clauses and required definitions; risk detection wants obligations, exceptions, and contradictions.

---

## Why It Matters
Query routing prevents the system from applying generic retrieval to specialized legal tasks. Correct routing improves evidence completeness and reduces unsupported reasoning.

---

## Inputs
- Raw user query.
- Optional conversation context.
- Optional user-selected jurisdiction, document set, language, or task mode.
- Query classification rules and threshold settings.

---

## Outputs
- `QueryRoute`
- query class
- retrieval mode selection
- graph expansion policy
- answer generation constraints

---

## Core Ideas
### Query Classes
| Query Class | Primary Need |
| --- | --- |
| Factual query | Exact answer from cited provision or definition. |
| Clause search | Find the clause, article, or section matching a topic or number. |
| Contract drafting | Retrieve clauses, definitions, conditions, and comparators for drafting support. |
| Risk detection | Retrieve obligations, exceptions, penalties, contradictions, and missing safeguards. |
| Legal explanation | Retrieve authoritative text plus surrounding interpretive context. |
| Cross-document comparison | Retrieve aligned provisions across versions or documents. |

### Routing Signals
- explicit citation or numbering
- request verbs such as define, compare, draft, assess, explain
- mention of risk, issue, contradiction, penalty, or missing clause
- user-selected scope
- language mismatch between query and corpus

### Multilingual Handling
- Detect query language.
- Normalize legal terms into retrieval aliases where possible.
- Route retrieval over corpus language variants while keeping original source language metadata intact.
- Do not translate source citations into fake local numbering systems.

---

## Pipeline
1. Normalize query text and extract explicit citation patterns.
2. Detect query language and legal-task signals.
3. Classify the query into one primary class and optional secondary class.
4. Apply scope constraints from user context.
5. Select retrieval modes and graph expansion policy.
6. Set response constraints such as citation strictness, comparison mode, or refusal sensitivity.
7. Emit `QueryRoute`.

---

## Rules
### ALWAYS
- Detect explicit citation patterns before semantic classification.
- Use user-specified jurisdiction or document scope when provided.
- Route drafting and risk tasks to broader evidence sets than factual lookup.
- Preserve multilingual context and query aliases.
- Record routing confidence and fallback class if ambiguity remains.

### NEVER
- Treat a citation lookup as a generic semantic question.
- Route comparison requests into single-document retrieval only.
- Ignore language mismatch between query and corpus.
- Use graph-heavy expansion for simple exact-number lookups unless first-pass evidence is incomplete.
- Hide routing ambiguity from downstream modules.

---

## Decision Logic
```text
if query contains explicit citation, article number, or clause number:
    class = clause_search
    retrieval = keyword + citation-aware + structure filters
elif query asks "what does", "define", or "where is":
    class = factual_query
    retrieval = hybrid with shallow graph expansion
elif query asks to draft, rewrite, or suggest clauses:
    class = contract_drafting
    retrieval = hybrid + graph expansion over definitions, obligations, and comparators
elif query asks about risk, missing terms, contradictions, or penalties:
    class = risk_detection
    retrieval = hybrid + contradiction-aware graph expansion
elif query asks to compare documents, versions, or jurisdictions:
    class = cross_document_comparison
    retrieval = hybrid + aligned structure retrieval + version-aware graph expansion
else:
    class = legal_explanation
    retrieval = hybrid with parent/child context expansion
```

Mode selection:
- graph retrieval only when structural or relational context is needed
- vector retrieval emphasized for paraphrased conceptual queries
- keyword retrieval emphasized for citations, defined terms, and article numbers
- hybrid retrieval default when intent is uncertain but answerable

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| User asks in one language about corpus in another | Route with multilingual alias expansion and preserve source-language citations. |
| Query mixes drafting and risk review | Set primary class to drafting and secondary class to risk; retrieve both example clauses and risk patterns. |
| Short query such as "Article 12" | Treat as clause search, not semantic retrieval. |
| User asks for "best clause" without scope | Route to drafting but require scoped evidence and mark recommendation basis. |
| Comparison of same law across versions | Use version-aware route and pair aligned articles or clauses. |
| Follow-up question references prior answer implicitly | Use conversation context only if prior evidence set is still in scope and version-compatible. |

---

## Data Model
`QueryRoute` fields:
- `query_id`
- `query_class`
- `secondary_classes[]`
- `language`
- `scope_filters`
- `retrieval_modes[]`
- `graph_policy`
- `response_constraints[]`
- `routing_confidence`

---

## Retrieval Impact
Routing determines which retrieval methods are activated, how far graph expansion goes, and how strict citation matching should be. This prevents under-retrieval for complex tasks and over-retrieval for simple lookups.

---

## GraphRAG Impact
Graph usage is query-class dependent. Routing ensures GraphRAG is used where structure or relations matter and avoided where it would only add noise.

---

## Logging
Always log:
- detected query signals
- chosen query class
- routing confidence
- selected retrieval modes
- scope filters
- multilingual normalization actions

---

## Validation
- Validate routing accuracy against labeled query sets.
- Validate that explicit citation queries hit clause-search routes.
- Validate multilingual routing behavior.
- Validate comparison routes preserve version and document separation.
- Review low-confidence routes and fallback behavior.

---

## Future Improvements
- Conversation-aware routing refinement.
- Better intent detection for mixed drafting and advisory tasks.
- Jurisdiction-specific query normalizers.
- Dynamic routing based on retrieval failure feedback.
