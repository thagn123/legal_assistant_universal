# Action Engine

## Goal
Allow the assistant to perform legal-related tasks, not only answer questions.

## Supported Actions
| Action | Required Evidence |
| --- | --- |
| Contract drafting | Uploaded law, templates, required clause patterns, jurisdiction metadata. |
| Compliance checking | Uploaded regulation plus target policy or contract. |
| Risk analysis | Contract clauses, obligations, exceptions, penalties, related provisions. |
| Clause recommendation | Similar clauses, missing-clause rules, document type context. |
| Legal summarization | Retrieved source evidence and hierarchy. |
| Cross-document reasoning | Aligned chunks, graph links, document/version metadata. |

## Action Safety Rules
Actions must:
- cite source evidence
- mark generated content as generated
- explain assumptions
- avoid claiming legal compliance unless evidence supports it
- preserve jurisdiction and document scope

Actions must not:
- draft clauses that claim compliance without evidence
- silently import legal knowledge outside uploaded documents
- rewrite source clauses as if they were original source text
- ignore conflicting uploaded evidence

## Drafting Policy
Drafting output is generated content. It must include:
- source basis
- assumptions
- missing information
- citations to uploaded evidence
- risk notes where applicable

## Risk Analysis Policy
Risk findings require:
- source clause or policy text
- relevant uploaded authority
- explanation of mismatch or uncertainty
- confidence and citation

## Compliance Policy
Compliance checks must compare:
```text
target document provision
  against
uploaded legal requirement
```

If either side is missing, the system must return partial or insufficient evidence.

