# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `76995ca7-9c20-42c1-942d-41c402086141`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-14T02:53:37.915629+00:00  
**Finished:** 2026-05-14T02:53:52.630982+00:00  
**Duration:** 14.72s  
**Overall Status:** ⚠️ `WARNING`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 0 |
| Warnings | ⚠️ 2 |
| Failed | ❌ 0 |

## ⚠️ Key Warnings

- '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.

---

## ⚠️ Document: `106_2025_QH15_628717.doc`

**Document ID:** `doc_6004e35ceb4c0814`  
**File Type:** `doc`  
**Extraction Strategy:** `long_local`  
**Overall Status:** `WARNING`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.05s | Loaded '106_2025_QH15_628717.doc' (type=doc, size=499,712 bytes) |
| document_profiling | ✅ pass | 5.32s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 2.97s | Extracted 1 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.01s | Structured 1 blocks, 0 tables, 0 sections, 0 articles, 0 clauses |
| cleaning_validation | ✅ pass | 0.01s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.03s | 1 chunks (0 degraded) using strategy=semantic |
| graph_building | ✅ pass | 0.00s | 2 nodes, 1 edges (0 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.02s | Tested 8 queries (vi) — 8 hit, 0 missed (hit rate 100%, avg 1.0 chunks/query) |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1 |
| Coverage Score | 1.00 |
| Degraded Blocks | 0 |
| Tables | 0 |
| Images | 0 |
| Sections | 0 |
| Articles | 0 |
| Clauses | 0 |
| Structure Detected | No |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 1 |
| Text Chunks | 1 |
| Table Chunks | 0 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 54949 |
| Strategy | semantic |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 2 |
| Total Edges | 1 |
| Structural Edges | 1 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Chunk": 1} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 8 |
| Queries with Results | 8 |
| Avg Result Count | 1.0 |

### Multilingual Metrics

| Metric | Value |
| --- | --- |
| Primary Language | `vi` |
| Language Confidence | 1.00 |
| Jurisdiction | `VN` |
| Canonical Refs Generated | 146 |
| Chunks with Canonical Refs | 1 |
| Chunks with Language Field | 1 |
| ALIAS_OF Edges | 0 |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.

---

## ⚠️ Document: `45_2019_QH14_333670.doc`

**Document ID:** `doc_aefcb4588f232b77`  
**File Type:** `doc`  
**Extraction Strategy:** `long_local`  
**Overall Status:** `WARNING`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.00s | Loaded '45_2019_QH14_333670.doc' (type=doc, size=482,816 bytes) |
| document_profiling | ✅ pass | 3.09s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 3.13s | Extracted 1 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.01s | Structured 1 blocks, 0 tables, 0 sections, 0 articles, 0 clauses |
| cleaning_validation | ✅ pass | 0.01s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.02s | 1 chunks (0 degraded) using strategy=semantic |
| graph_building | ✅ pass | 0.00s | 2 nodes, 1 edges (0 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.02s | Tested 8 queries (vi) — 8 hit, 0 missed (hit rate 100%, avg 1.0 chunks/query) |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1 |
| Coverage Score | 1.00 |
| Degraded Blocks | 0 |
| Tables | 0 |
| Images | 0 |
| Sections | 0 |
| Articles | 0 |
| Clauses | 0 |
| Structure Detected | No |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 1 |
| Text Chunks | 1 |
| Table Chunks | 0 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 47320 |
| Strategy | semantic |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 2 |
| Total Edges | 1 |
| Structural Edges | 1 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Chunk": 1} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 8 |
| Queries with Results | 8 |
| Avg Result Count | 1.0 |

### Multilingual Metrics

| Metric | Value |
| --- | --- |
| Primary Language | `vi` |
| Language Confidence | 1.00 |
| Jurisdiction | `VN` |
| Canonical Refs Generated | 261 |
| Chunks with Canonical Refs | 1 |
| Chunks with Language Field | 1 |
| ALIAS_OF Edges | 0 |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.

---
