# Hallucination Safety And Observability

## Goal
Define quality gates that make extraction, retrieval, graph construction, and reasoning auditable.

## Hallucination Prevention
Never allow:
- invented legal text
- invented table cells
- invented citations
- unsupported legal claims
- hidden use of model memory as authority

Always require:
- retrieved evidence
- source anchors
- confidence
- degraded flags
- refusal behavior when evidence is insufficient

## Parser Benchmark Metrics
| Metric | Meaning |
| --- | --- |
| Pages parsed | Source pages vs extracted pages. |
| Blocks extracted | Content units produced. |
| OCR confidence | Reliability of scan/image text. |
| Tables extracted | Count and topology confidence. |
| Parse errors | Stage failures and warnings. |
| Chunk count | Retrieval units produced. |
| Graph nodes/edges | Knowledge graph coverage. |
| Retrieval smoke hit rate | Basic retrieval health. |
| Multilingual metrics | Language, canonical refs, alias edges, cross-language hit rate. |

## Required Logs
The system must log:
- extraction decisions
- OCR decisions
- parser cleanup
- chunking decisions
- graph build counts
- retrieval signals
- validation failures
- answer support states

## Evidence Quality States
| State | Meaning | Use In Answers |
| --- | --- | --- |
| `authoritative` | High confidence and provenance complete. | Can be cited. |
| `degraded` | Low confidence or partial extraction. | Cite with warning or avoid. |
| `unresolved` | Ambiguous or incomplete. | Do not rely on as authority. |
| `missing` | Required evidence absent. | Refuse or narrow scope. |

## Regression Gates
Block release when:
- invented text is detected
- no blocks are extracted from valid files
- graph edges lack provenance
- chunking splits prohibited legal units
- chunk-to-chunk alias edges appear
- retrieval cannot find direct article references in structured documents

