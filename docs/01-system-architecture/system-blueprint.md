# System Blueprint

## Goal
Define the end-to-end architecture for the Adaptive Legal Multimodal GraphRAG Assistant.

## High-Level Flow
```text
Documents
  -> Document Intelligence Pipeline
  -> Structured Legal Representation
  -> Legal Knowledge Graph
  -> Hybrid Retrieval
  -> Evidence-Grounded Legal Reasoning
  -> Action Generation
```

## System Layers
| Layer | Responsibility | Main Outputs |
| --- | --- | --- |
| Document Intelligence | Understand documents and preserve source evidence. | Canonical document, blocks, tables, images, validation status. |
| Knowledge Structuring | Organize extracted legal knowledge into hierarchy and graph-ready units. | Sections, articles, clauses, entities, canonical refs. |
| Retrieval System | Retrieve accurate evidence from chunks, metadata, keywords, vectors, and graph. | Ranked evidence set. |
| Legal Reasoning | Reason only from retrieved evidence. | Citation-backed answer or refusal. |
| Action Engine | Execute legal-related tasks using retrieved evidence. | Drafts, risk reports, clause recommendations, compliance findings. |

## Runtime Pipeline
```text
Upload File
  -> Input Loading
  -> Document Profiling
  -> Complexity Detection
  -> Layout Analysis
  -> Adaptive Extraction
  -> Canonical Structuring
  -> Cleaning and Validation
  -> Semantic Chunking
  -> Graph Construction
  -> Indexing
  -> Retrieval Smoke Test / Query Runtime
```

## Current Repo Mapping
| Architecture Stage | Current Code |
| --- | --- |
| Input loading | `src/pipeline/stages.py::stage_input_loading` |
| Document profiling | `src/pipeline/stages.py::stage_document_profiling` |
| Extraction | `src/pipeline/stages.py::stage_extraction` |
| Canonical structuring | `src/pipeline/stages.py::stage_canonical_structuring` |
| Cleaning and validation | `src/pipeline/stages.py::stage_cleaning_validation` |
| Chunking | `src/pipeline/stages.py::stage_chunking` |
| Graph building | `src/pipeline/stages.py::stage_graph_building` |
| Retrieval smoke test | `src/pipeline/stages.py::stage_retrieval_smoke_test` |
| Orchestration | `src/pipeline/orchestrator.py` |
| Reports | `src/evaluation/reports.py` |

## Architectural Principles
- Local-first extraction is the default.
- AI repair is optional, targeted, and gated by configuration.
- Canonical structured representation is the source of truth.
- Tables and images are evidence objects, not discarded decoration.
- Chunks are retrieval units, not source-of-truth objects.
- GraphRAG augments retrieval; it does not replace evidence.
- Legal reasoning must cite retrieved source evidence.

## Non-Goals
- General legal advice without evidence.
- Static legal expert system for one country only.
- Full production SaaS backend in the current pipeline evaluator.
- Autonomous filing or legal decision execution.

