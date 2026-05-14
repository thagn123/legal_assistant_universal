# Evidence-Grounded Legal Reasoning

## Goal
Produce legal answers and analyses using only retrieved uploaded evidence.

## Reasoning Contract
The reasoning layer receives:
- user query
- query class
- retrieved evidence set
- citations and source anchors
- confidence and degraded flags
- graph paths used for expansion

The reasoning layer returns:
- answer
- cited evidence references
- limitations
- uncertainty
- refusal when evidence is insufficient

## Required Behavior
The system must:
- cite source articles, clauses, tables, or images
- separate source quotes from generated explanation
- explain evidence gaps
- show uncertainty for low-confidence evidence
- restrict reasoning to uploaded content

## Forbidden Behavior
The system must not:
- hallucinate laws
- invent clauses
- create unsupported legal references
- answer from general model knowledge when uploaded evidence is required
- hide conflicts between retrieved sources

## Query Classes
| Query Class | Evidence Needed |
| --- | --- |
| Factual legal question | Direct source clause or article. |
| Clause search | Exact structure match or highly relevant clause chunk. |
| Contract drafting | Source-backed clauses, definitions, risk constraints. |
| Compliance checking | Policy text plus applicable uploaded regulation. |
| Risk analysis | Clauses, obligations, penalties, exceptions, contradictions. |
| Cross-document comparison | Aligned provisions and version/jurisdiction metadata. |

## Answer States
| State | Meaning |
| --- | --- |
| `supported` | Evidence directly supports the answer. |
| `partially_supported` | Some evidence exists but gaps remain. |
| `unsupported` | Required evidence is missing; refuse or narrow answer. |

## Example Reasoning Flow
```text
User asks: Can this employee legally be terminated?
  -> classify as risk/compliance question
  -> retrieve uploaded labor law termination articles
  -> retrieve employment contract termination clause
  -> expand to exceptions, notice requirements, penalties
  -> compare evidence
  -> answer with citations and limitations
```

