# Implementation Roadmap

## Goal
Guide implementation from the current repo state toward a robust Adaptive Legal Multimodal GraphRAG Assistant.

## Phase 1: Stabilize Current Pipeline
Priority:
- fix encoding/mojibake in docs, logs, report strings, and source comments
- standardize strategy naming
- clean repo hygiene around pycache and generated reports
- verify `MULTILINGUAL_UPGRADE_LOG.md` claims against code behavior
- add regression checks for multilingual retrieval and alias edges

Exit criteria:
- reports render clean UTF-8 text
- no chunk-to-chunk `ALIAS_OF` edges
- sample VI/EN documents pass retrieval smoke tests
- long DOC/DOCX files produce structured chunks

## Phase 2: Strengthen Document Intelligence
Priority:
- isolate profiling, extraction, structuring, validation, chunking, graph, retrieval stages into smaller modules
- improve table extraction and table topology warnings
- formalize OCR confidence and image evidence states
- add parser-noise metrics to evaluation reports

Exit criteria:
- stage modules can be unit-tested separately
- tables and images have explicit degraded status when fidelity is not preserved
- parser noise cleanup is logged and measurable

## Phase 3: Complete GraphRAG Runtime
Priority:
- implement query router
- implement graph traversal policy
- assemble evidence bundles
- integrate graph-expanded evidence into reasoning interface

Exit criteria:
- queries can retrieve by citation, concept, alias, and graph expansion
- graph traversal has confidence and depth limits
- evidence bundles preserve source paths and citations

## Phase 4: Add Action Engine
Priority:
- implement action request schema
- implement drafting/risk/compliance workflows
- add evidence support validation before output
- mark generated content separately from source content

Exit criteria:
- drafting output includes source basis and assumptions
- risk analysis cites clauses and uploaded authority
- unsupported tasks return limitation/refusal

## Phase 5: Production Architecture
Priority:
- API service
- async job queue
- persistent storage for documents, chunks, graph, logs
- authentication and access control
- deployment and monitoring

Exit criteria:
- ingestion jobs are resumable
- artifacts are versioned
- users can query uploaded document spaces
- audit logs are available for every answer

