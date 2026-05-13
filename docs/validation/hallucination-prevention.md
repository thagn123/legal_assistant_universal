# Hallucination Prevention

## Goal
Define the system-wide controls that prevent invented text, unsupported legal claims, false citations, and overconfident answers.

---

## Problem
Legal users may interpret system output as authoritative. If the system fills gaps with plausible but unsupported content, the error can be operationally severe.

---

## Why It Matters
Hallucination control is a first-order design goal, not a post-processing improvement. It depends on extraction fidelity, retrieval sufficiency, confidence handling, and refusal behavior.

---

## Inputs
- Canonical document artifacts and validation status.
- Retrieval evidence set and citation coverage summary.
- Graph traversal paths and confidence metadata.
- Answer generation request and query class.

---

## Outputs
- answer safety decision
- support status: supported, partially supported, unsupported
- response constraints
- refusal or limitation message when required

---

## Core Ideas
### No Invention Rule
The system must never:
- invent missing legal text
- invent missing table cells
- invent citations or targets
- infer that a clause exists when retrieval did not find it

### No Unsupported Claims Rule
Every material legal claim in a response must map to retrieved evidence. Unsupported reasoning is not allowed to cross the answer boundary.

### Citation Requirement
- Factual legal answers require direct citation anchors.
- Explanatory answers require citation for each substantive proposition.
- Drafting and recommendation outputs require source-basis citations or explicit indication that language is suggested, not quoted.

### Confidence Handling
- low-confidence source evidence reduces answer authority
- unsupported expansions must be excluded
- ambiguous citations must remain ambiguous

### Answer States
| State | Meaning |
| --- | --- |
| Supported | Evidence directly supports the answer and citations are present. |
| Partially supported | Some aspects are supported, but important gaps or ambiguities remain. |
| Unsupported | Evidence is missing or too weak; answer must refuse or narrow scope. |

---

## Pipeline
1. Receive query, evidence set, and answer intent.
2. Check evidence sufficiency for the requested task.
3. Verify citation coverage and provenance completeness.
4. Check confidence and degradation flags across core evidence items.
5. Allow answer generation only within the supported evidence envelope.
6. Force limitation statements or refusal when support is partial or missing.
7. Validate final answer claims against evidence references before return.

---

## Rules
### ALWAYS
- Require evidence for every material claim.
- Surface uncertainty explicitly.
- Refuse when retrieval is incomplete for an authoritative answer.
- Preserve distinction between quoted source language and generated explanation.
- Validate final citations before response delivery.

### NEVER
- Present generated language as quoted source text.
- Hide missing evidence behind generic confidence phrasing.
- Convert low-confidence OCR fragments into definitive legal claims.
- Use graph adjacency alone as legal proof.
- Continue generation after support validation fails.

---

## Decision Logic
```text
if evidence_set is empty:
    refuse
elif required citations are missing:
    return partial or refuse based on task criticality
elif core evidence confidence < answer_threshold:
    narrow scope or refuse
elif retrieved evidence does not cover all requested subquestions:
    answer supported parts only and mark gaps
else:
    generate cited answer
```

Task strictness:
- factual lookup: highest strictness
- clause search: high strictness
- legal explanation: high strictness with scoped explanation allowed
- drafting: allow generated language only when evidence basis is explicit
- risk detection: require evidence-backed rationale for each flagged risk

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| User asks about clause not found in corpus | Refuse the existence claim and report retrieval gap. |
| Retrieved sources conflict | Surface both sources and avoid synthesizing one rule unless the conflict is resolved by authority or version metadata. |
| OCR only partially recovers a clause | Quote only readable fragments and mark incompleteness. |
| User asks for recommendation beyond corpus scope | Provide only source-backed options or refuse unsupported recommendation. |
| Graph suggests relation without direct text evidence | Use relation for retrieval only, not as a standalone claim. |
| Drafting request needs absent jurisdiction-specific rule | State limitation and avoid claiming compliance. |

---

## Data Model
`AnswerSafetyDecision` fields:
- `query_id`
- `support_state`
- `coverage_score`
- `citation_coverage_score`
- `min_evidence_confidence`
- `unsupported_claim_flags[]`
- `refusal_required`
- `allowed_response_modes[]`

---

## Retrieval Impact
This policy forces retrieval to be evaluated for sufficiency, not just relevance. It increases the importance of citation coverage, version correctness, and evidence completeness in ranking and fallback behavior.

---

## GraphRAG Impact
Graph expansion may improve support completeness, but graph-derived relations are only admissible when backed by anchored source evidence. The graph remains a retrieval aid, not an authority substitute.

---

## Logging
Always log:
- support state
- unsupported claim triggers
- citation coverage gaps
- refusal reasons
- degraded evidence contribution
- final answer validation outcome

---

## Validation
- Test refusal behavior on missing-evidence queries.
- Test citation coverage checks on partial answers.
- Validate claim-to-citation alignment in generated responses.
- Track false-support incidents as critical defects.
- Audit supported vs partially supported answer labeling.

---

## Future Improvements
- Automated claim-to-evidence alignment scoring.
- Stronger contradiction detection prior to answer generation.
- User-visible evidence sufficiency explanations.
- Human escalation workflows for high-risk unsupported queries.
