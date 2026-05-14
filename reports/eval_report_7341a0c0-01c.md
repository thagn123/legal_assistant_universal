# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `7341a0c0-01cd-4f31-807e-b2fffe96ab9f`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-14T03:22:48.214303+00:00  
**Finished:** 2026-05-14T03:23:01.666415+00:00  
**Duration:** 13.45s  
**Overall Status:** ⚠️ `WARNING`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 0 |
| Warnings | ⚠️ 2 |
| Failed | ❌ 0 |

## ⚠️ Key Warnings

- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1147 duplicates doc_aefcb4588f232b77__p0001_r000_b1124
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0080 duplicates doc_6004e35ceb4c0814__p0001_r000_b0067
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0253 duplicates doc_aefcb4588f232b77__p0001_r000_b0230
- No results for query: 'bên'
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1169 duplicates doc_aefcb4588f232b77__p0001_r000_b1146
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1317 duplicates doc_aefcb4588f232b77__p0001_r000_b1109
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1315 duplicates doc_aefcb4588f232b77__p0001_r000_b1105
- '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1170 duplicates doc_aefcb4588f232b77__p0001_r000_b1124
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0072 duplicates doc_6004e35ceb4c0814__p0001_r000_b0052
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1316 duplicates doc_aefcb4588f232b77__p0001_r000_b1108
- No results for query: 'khoản'

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
| document_profiling | ✅ pass | 1.42s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 5.81s | Extracted 1258 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.04s | Structured 1258 blocks, 0 tables, 13 sections, 116 articles, 0 clauses |
| cleaning_validation | ⚠️ warning | 0.01s | 2 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.01s | 116 chunks (0 degraded) using strategy=long_local_structural |
| graph_building | ✅ pass | 0.00s | 246 nodes, 245 edges (0 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.01s | Tested 8 queries (vi) — 7 hit, 1 missed (hit rate 88%, avg 12.4 chunks/query) |  |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1258 |
| Coverage Score | 1.00 |
| Degraded Blocks | 2 |
| Tables | 0 |
| Images | 0 |
| Sections | 13 |
| Articles | 116 |
| Clauses | 0 |
| Structure Detected | Yes |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 116 |
| Text Chunks | 116 |
| Table Chunks | 0 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 53 |
| Strategy | long_local_structural |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 246 |
| Total Edges | 245 |
| Structural Edges | 245 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Section": 13, "Article": 116, "Chunk": 116} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 8 |
| Queries with Results | 7 |
| Avg Result Count | 12.4 |
| Failed Queries | bên |

### Multilingual Metrics

| Metric | Value |
| --- | --- |
| Primary Language | `vi` |
| Language Confidence | 1.00 |
| Jurisdiction | `VN` |
| Canonical Refs Generated | 236 |
| Chunks with Canonical Refs | 116 |
| Chunks with Language Field | 116 |
| ALIAS_OF Edges | 0 |
| Cross-lang Queries Tested | 3 |
| Cross-lang Hit Rate | 100% |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0072 duplicates doc_6004e35ceb4c0814__p0001_r000_b0052
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0080 duplicates doc_6004e35ceb4c0814__p0001_r000_b0067
- ⚠️ No results for query: 'bên'

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
| document_profiling | ✅ pass | 2.99s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 2.99s | Extracted 1329 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.05s | Structured 1329 blocks, 0 tables, 41 sections, 220 articles, 0 clauses |
| cleaning_validation | ⚠️ warning | 0.01s | 7 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.03s | 220 chunks (0 degraded) using strategy=long_local_structural |
| graph_building | ✅ pass | 0.01s | 482 nodes, 481 edges (0 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.01s | Tested 8 queries (vi) — 7 hit, 1 missed (hit rate 88%, avg 12.6 chunks/query) |  |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1329 |
| Coverage Score | 1.00 |
| Degraded Blocks | 7 |
| Tables | 0 |
| Images | 0 |
| Sections | 41 |
| Articles | 220 |
| Clauses | 0 |
| Structure Detected | Yes |

### Chunk Metrics

| Metric | Value |
| --- | --- |
| Total Chunks | 220 |
| Text Chunks | 220 |
| Table Chunks | 0 |
| Degraded Chunks | 0 |
| Avg Token Estimate | 52 |
| Strategy | long_local_structural |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 482 |
| Total Edges | 481 |
| Structural Edges | 481 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1, "Section": 41, "Article": 220, "Chunk": 220} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 8 |
| Queries with Results | 7 |
| Avg Result Count | 12.6 |
| Failed Queries | khoản |

### Multilingual Metrics

| Metric | Value |
| --- | --- |
| Primary Language | `vi` |
| Language Confidence | 1.00 |
| Jurisdiction | `VN` |
| Canonical Refs Generated | 443 |
| Chunks with Canonical Refs | 220 |
| Chunks with Language Field | 220 |
| ALIAS_OF Edges | 0 |
| Cross-lang Queries Tested | 3 |
| Cross-lang Hit Rate | 100% |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0253 duplicates doc_aefcb4588f232b77__p0001_r000_b0230
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1147 duplicates doc_aefcb4588f232b77__p0001_r000_b1124
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1169 duplicates doc_aefcb4588f232b77__p0001_r000_b1146
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1170 duplicates doc_aefcb4588f232b77__p0001_r000_b1124
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1315 duplicates doc_aefcb4588f232b77__p0001_r000_b1105
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1316 duplicates doc_aefcb4588f232b77__p0001_r000_b1108
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1317 duplicates doc_aefcb4588f232b77__p0001_r000_b1109
- ⚠️ No results for query: 'khoản'

---
