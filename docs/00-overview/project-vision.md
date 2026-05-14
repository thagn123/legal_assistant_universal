# Project Vision

## System Name
Adaptive Legal Multimodal GraphRAG Assistant.

Preferred positioning:
- Adaptive Legal Intelligence System
- Legal Multimodal Knowledge Operating System
- Evidence-Grounded Legal Intelligence Platform

Avoid describing the system as:
- simple legal chatbot
- basic RAG application
- PDF parser
- summarization tool

## Mission
Build AI legal infrastructure that can understand, structure, retrieve, reason, and act on legal knowledge uploaded by users.

The system is data-driven. It does not depend on fixed country-specific rules. It adapts to uploaded legal documents from different jurisdictions, industries, formats, and languages.

## Core Formula
```text
Local-first extraction
+ AI-assisted repair
+ Structure-preserving processing
+ Graph-aware retrieval
+ Evidence-grounded reasoning
+ Strict hallucination prevention
= Reliable Legal AI System
```

## Main Goal
Allow users to upload legal knowledge from any jurisdiction or industry and let the system:
- understand documents
- structure legal knowledge
- build semantic relationships
- retrieve accurate evidence
- reason based on uploaded data
- execute legal-related actions

## System Boundary
The system may:
- process legal source documents
- preserve legal structure and evidence
- answer with citations from uploaded evidence
- draft or recommend content based on retrieved evidence
- detect risks, contradictions, missing clauses, and compliance gaps

The system must not:
- invent laws or clauses
- answer outside retrieved evidence
- represent output as legal advice without review
- silently merge conflicting sources
- rewrite source text during extraction

## Design Constraints
| Constraint | Required Behavior |
| --- | --- |
| Jurisdiction independence | Use uploaded evidence and metadata; avoid hardcoded country rules. |
| Multimodal input | Support text, scans, tables, images, and mixed layouts. |
| Legal traceability | Preserve source document, page, block, citation, and confidence. |
| Retrieval quality | Optimize chunking and graph traversal for legal evidence retrieval. |
| Hallucination prevention | Refuse or limit answers when evidence is missing. |

## Success Criteria
- Simple and long text documents process locally with high fidelity.
- Tables and images are preserved as first-class evidence objects.
- Chunks preserve article, clause, table, and hierarchy context.
- Graph nodes and edges preserve structure, references, dependencies, and evidence.
- Retrieval combines keyword, semantic, metadata, citation, and graph signals.
- Legal reasoning cites uploaded evidence and exposes uncertainty.
- Logs and benchmark reports make every stage auditable.

