# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `1a7619d4-e2c4-445e-bb6a-a9eb9aa72795`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-13T04:29:00.301665+00:00  
**Finished:** 2026-05-13T04:29:00.754050+00:00  
**Duration:** 0.45s  
**Overall Status:** ❌ `FAIL`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 1 |
| Warnings | ⚠️ 0 |
| Failed | ❌ 1 |

## ⚠️ Key Warnings

- No results for query: 'Article 3 — Fees and Payment'
- No results for query: 'Article 1 — Definitions'
- No results for query: 'Article 2 — Scope of Services'

## 💡 Recommendations

- Some documents failed. Check logs in the output/logs/ directory.

---

## ✅ Document: `sample_contract.html`

**Document ID:** `doc_edd4c13282a800eb`  
**File Type:** `html`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `PASS`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.07s | Loaded 'sample_contract.html' (type=html, size=5,983 bytes) |
| document_profiling | ✅ pass | 0.00s | Strategy: simple_local | pages=0 | tables=True |
| extraction | ✅ pass | 0.36s | Extracted 44 blocks, 1 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 44 blocks, 1 tables, 6 sections, 14 articles, 0 clauses |
| cleaning_validation | ✅ pass | 0.00s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.00s | 15 chunks (0 degraded) using strategy=structural |
| graph_building | ✅ pass | 0.00s | 37 nodes, 36 edges created |
| retrieval_smoke_test | ✅ pass | 0.00s | Tested 3 queries. Avg hits: 1.0. Failed: 0 |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
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
| Avg Token Estimate | 11 |
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
| Queries Tested | 3 |
| Queries with Results | 3 |
| Avg Result Count | 1.0 |

---

## ❌ Document: `sample_hop_dong_viet.html`

**Document ID:** `doc_9db3b5049432ef95`  
**File Type:** `html`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `FAIL`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.00s | Loaded 'sample_hop_dong_viet.html' (type=html, size=7,492 bytes) |
| document_profiling | ✅ pass | 0.00s | Strategy: simple_local | pages=0 | tables=True |
| extraction | ✅ pass | 0.00s | Extracted 51 blocks, 1 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 51 blocks, 1 tables, 6 sections, 14 articles, 9 clauses |
| cleaning_validation | ✅ pass | 0.00s | 0 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.00s | 15 chunks (0 degraded) using strategy=structural |
| graph_building | ✅ pass | 0.00s | 37 nodes, 36 edges created |
| retrieval_smoke_test | ❌ fail | 0.00s | Tested 3 queries. Avg hits: 0.0. Failed: 3 |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
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
| Avg Token Estimate | 11 |
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
| Queries Tested | 3 |
| Queries with Results | 0 |
| Avg Result Count | 0.0 |
| Failed Queries | Article 1 — Definitions, Article 2 — Scope of Services, Article 3 — Fees and Payment |

### Warnings

- ⚠️ No results for query: 'Article 1 — Definitions'
- ⚠️ No results for query: 'Article 2 — Scope of Services'
- ⚠️ No results for query: 'Article 3 — Fees and Payment'

---
