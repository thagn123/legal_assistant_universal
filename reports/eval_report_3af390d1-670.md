# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `3af390d1-6701-4fe5-b77f-88495839cafc`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-13T04:33:03.288074+00:00  
**Finished:** 2026-05-13T04:33:03.502413+00:00  
**Duration:** 0.21s  
**Overall Status:** ✅ `PASS`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 2 |
| Warnings | ⚠️ 0 |
| Failed | ❌ 0 |

## ⚠️ Key Warnings

- No results for query: 'section'
- No results for query: 'mục'
- No results for query: 'bên'
- No results for query: 'clause'

---

## ✅ Document: `sample_contract.html`

**Document ID:** `doc_edd4c13282a800eb`  
**File Type:** `html`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `PASS`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.05s | Loaded 'sample_contract.html' (type=html, size=5,983 bytes) |
| document_profiling | ✅ pass | 0.00s | Strategy: simple_local | pages=1 | tables=True |
| extraction | ✅ pass | 0.14s | Extracted 44 blocks, 1 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 44 blocks, 1 tables, 6 sections, 14 articles, 0 clauses |
| cleaning_validation | ✅ pass | 0.00s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.00s | 15 chunks (0 degraded) using strategy=structural |
| graph_building | ✅ pass | 0.00s | 37 nodes, 36 edges created |
| retrieval_smoke_test | ✅ pass | 0.00s | Tested 7 queries — 5 hit, 2 missed (hit rate 71%, avg 4.6 chunks/query) |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 1 |
| Pages (extracted) | 1 |
| Blocks | 44 |
| Coverage Score | 1.00 |
| Degraded Blocks | 0 |
| Tables | 1 |
| Images | 0 |
| Sections | 6 |
| Articles | 14 |
| Clauses | 0 |
| Structure Detected | Yes |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 15 |
| Text Chunks | 14 |
| Table Chunks | 1 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 35 |
| Strategy | structural |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 37 |
| Total Edges | 36 |
| Structural Edges | 36 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Section": 6, "Article": 14, "Table": 1, "Chunk": 15} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 7 |
| Queries with Results | 5 |
| Avg Result Count | 4.6 |
| Failed Queries | clause, section |

### Warnings

- ⚠️ No results for query: 'clause'
- ⚠️ No results for query: 'section'

---

## ✅ Document: `sample_hop_dong_viet.html`

**Document ID:** `doc_9db3b5049432ef95`  
**File Type:** `html`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `PASS`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.00s | Loaded 'sample_hop_dong_viet.html' (type=html, size=7,492 bytes) |
| document_profiling | ✅ pass | 0.00s | Strategy: simple_local | pages=1 | tables=True |
| extraction | ✅ pass | 0.00s | Extracted 51 blocks, 1 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 51 blocks, 1 tables, 6 sections, 14 articles, 9 clauses |
| cleaning_validation | ✅ pass | 0.00s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.00s | 15 chunks (0 degraded) using strategy=structural |
| graph_building | ✅ pass | 0.00s | 37 nodes, 36 edges created |
| retrieval_smoke_test | ✅ pass | 0.00s | Tested 8 queries — 6 hit, 2 missed (hit rate 75%, avg 5.0 chunks/query) |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 1 |
| Pages (extracted) | 1 |
| Blocks | 51 |
| Coverage Score | 1.00 |
| Degraded Blocks | 0 |
| Tables | 1 |
| Images | 0 |
| Sections | 6 |
| Articles | 14 |
| Clauses | 9 |
| Structure Detected | Yes |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 15 |
| Text Chunks | 14 |
| Table Chunks | 1 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 33 |
| Strategy | structural |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 37 |
| Total Edges | 36 |
| Structural Edges | 36 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Section": 6, "Article": 14, "Table": 1, "Chunk": 15} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 8 |
| Queries with Results | 6 |
| Avg Result Count | 5.0 |
| Failed Queries | bên, mục |

### Warnings

- ⚠️ No results for query: 'bên'
- ⚠️ No results for query: 'mục'

---
