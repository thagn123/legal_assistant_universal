# Project Generator Prompt (AI-Readable)

## Goal
Provide a single prompt that an AI coding agent can use to generate/complete this repository into a working Legal Multimodal GraphRAG system, aligned with the existing `docs/` contracts and the current `src/` skeleton.

---

## Problem
AI agents can drift from spec, invent behaviors, or implement unsafe AI extraction. This prompt constrains the agent to implement deterministically, local-first, provenance-preserving, and testable behavior.

---

## Why It Matters
This repository is legal-oriented. Incorrect extraction, wrong citations, or invented text is unacceptable. A generator prompt must enforce strict guardrails and require measurable validation.

---

## Inputs
- Repo root containing:
  - `docs/` specification set (source of truth)
  - `src/` python pipeline implementation
  - `requirements.txt`
  - `samples/` and `raw_data/` (if present)
- Target deliverables:
  - runnable pipeline evaluation
  - correct local-first parsing
  - selective AI-assisted repair (optional, gated)
  - chunking optimized for retrieval
  - graph building aligned with schema
  - logs and benchmark outputs

---

## Outputs
An implementation agent must produce:
- Working pipeline run command(s).
- Deterministic extraction for simple and long documents.
- Region-level AI escalation only for tables/images/scans when enabled.
- Canonical outputs in HTML or Markdown derived from canonical objects.
- Chunk sets and graph subgraphs with provenance and confidence.
- Logs and evaluation reports that support debugging.
- Tests or evaluation checks that prevent regressions.

---

## Core Ideas
### Non-Negotiables (Hard Constraints)
- Preserve source content faithfully.
- Never invent missing legal text or table cells.
- Never summarize during extraction.
- Preserve structure and hierarchy when it exists.
- Prefer local-first extraction.
- Use AI only when local extraction is insufficient AND only on targeted regions.
- Keep tables intact whenever possible.
- Preserve headings, article numbers, clauses, sections, and hierarchy.
- Keep page references and source traceability.
- Everything must be designed for retrieval, citation, and GraphRAG.

### Existing Repo Contracts
You must treat the following as contracts:
- `docs/project-context.md`
- `docs/parsing/document-intelligence-pipeline.md`
- `docs/chunking/chunking-strategies.md`
- `docs/chunking/chunking-decision-tree.md`
- `docs/graphrag/graph-schema.md`
- `docs/graphrag/graph-builder.md`
- `docs/graphrag/traversal-and-expansion.md`
- `docs/retrieval/hybrid-retrieval.md`
- `docs/retrieval/query-routing.md`
- `docs/validation/hallucination-prevention.md`
- `docs/validation/parser-benchmark.md`
- `docs/logging/observability.md`
- `docs/prompts/*`
- `docs/schemas/document-schema.md`

### Target Strategy Variants (Must Implement)
- `simple_local`: fast deterministic extraction for simple docs.
- `long_local`: deterministic extraction for long text-dominant docs; region overrides allowed.
- `hybrid_region_precision`: local extraction for most regions + precision handling for table/image/mixed regions.
- `scan_recovery`: OCR-first flow with strict confidence gating and repair options.

---

## Pipeline
Implementation steps the agent must follow:
1. Read and comply with all `docs/` contracts; do not invent new schema fields casually.
2. Audit `src/` code for mismatches vs docs and fix them conservatively.
3. Ensure `src/config.py` thresholds and toggles match routing logic and are logged.
4. Verify `src/utils/logging.py` conforms to `docs/logging/observability.md`:
   - Do not conflate stage outcome status with log severity level.
5. Ensure parsing stages preserve:
   - raw vs cleaned text separation
   - source offsets and provenance
   - table and image first-class objects
6. Implement parser-noise cleanup only when reversible and logged; do not delete meaningful legal text.
7. Implement chunking strategies and decision tree:
   - prohibited split rules enforced
   - table header preservation
   - sibling evidence chunks for tables/images
8. Implement graph building strictly per graph schema:
   - structure first
   - citations next
   - conservative semantic edges last
9. Implement hybrid retrieval and query routing:
   - citation-aware exact matching
   - multilingual alias expansion
   - optional graph expansion with stop rules
10. Implement validation and benchmarking:
   - extraction accuracy signals
   - table fidelity checks
   - parser noise checks
   - retrieval smoke tests
   - graph provenance checks
11. Produce runnable commands and ensure outputs are written under `reports/`.

---

## Rules
### ALWAYS
- Use local deterministic methods by default.
- Keep AI features behind config flags; default is off.
- Log every routing decision with thresholds used.
- Keep provenance (`trace_id`, `document_id`, `source_hash`) on all artifacts.
- Refuse to produce authoritative answers when evidence is insufficient.

### NEVER
- Generate or “restore” text you cannot see in the source.
- Merge conflicting versions silently.
- Create graph edges without provenance.
- Flatten tables into prose-only output when a table structure exists.
- Hide low-confidence OCR content from validation.

---

## Decision Logic
When deciding whether to implement or refactor:
```text
if change improves correctness, provenance, or hallucination safety:
    do it, with tests/logging
elif change is cosmetic or refactor-only and risks regressions:
    defer unless required for correctness
```

AI escalation gating:
```text
if enable_ai_repair is False:
    never call AI
elif region_type in {table, image, mixed} and confidence below threshold:
    call AI only on that region with no-invention constraints
elif strict_accuracy_mode is True and region_type in {table, image}:
    allow AI verification bounded to evidence comparison
else:
    keep local output
```

---

## Edge Cases
| Case | Required Behavior |
| --- | --- |
| Bilingual documents | Preserve both language streams; do not merge. |
| OCR degraded | Mark degraded; restrict authority usage; keep raw OCR. |
| Ambiguous citations | Keep unresolved or multi-candidate; do not force resolution. |
| Borderless tables | Attempt deterministic alignment; if failed and AI enabled, repair topology only. |
| Stamps/signatures | Preserve as image evidence; avoid semantic inference. |

---

## Data Model
You must implement against canonical objects in `src/schemas/*` and ensure they match `docs/schemas/document-schema.md`.
If you change the schema:
- update docs and code together
- bump `schema_version` and/or `processing_version`
- add migration notes in logs

---

## Retrieval Impact
Prioritize correctness and citation safety over broad recall. Retrieval must return the right clause/table/definition and preserve context required for legal meaning.

---

## GraphRAG Impact
GraphRAG must remain conservative:
- structure and citation edges dominate traversal
- semantic edges require explicit evidence
- traversal must stop early to avoid noise

---

## Logging
Required:
- stage start/end
- routing decisions (strategy + thresholds)
- parser QA actions (noise suppression)
- AI invocation reasons and validation outcome
- validation failures and refusal triggers

---

## Validation
Release gate:
- zero invented text incidents
- canonical provenance completeness
- stable chunk boundaries with prohibited-split checks passing
- graph schema validation passing
- retrieval smoke tests passing for:
  - exact article lookup
  - cross-language alias match

---

## Future Improvements
- Production service layer (API + storage + async workers).
- Stronger table topology benchmark set.
- Learned routing calibration from benchmark outcomes.
- Human review workflows for low-confidence evidence.

