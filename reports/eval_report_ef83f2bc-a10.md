# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `ef83f2bc-a103-4037-a84e-fb4a9da1ef91`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-14T03:04:28.123961+00:00  
**Finished:** 2026-05-14T03:04:43.102910+00:00  
**Duration:** 14.98s  
**Overall Status:** ⚠️ `WARNING`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 0 |
| Warnings | ⚠️ 2 |
| Failed | ❌ 0 |

## ⚠️ Key Warnings

- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0150 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1183 duplicates doc_aefcb4588f232b77__p0001_r000_b1135
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1329 duplicates doc_aefcb4588f232b77__p0001_r000_b1117
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0849 duplicates doc_6004e35ceb4c0814__p0001_r000_b0660
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0767 duplicates doc_6004e35ceb4c0814__p0001_r000_b0660
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1330 duplicates doc_aefcb4588f232b77__p0001_r000_b1118
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0143 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- No results for query: 'khoản'
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1182 duplicates doc_aefcb4588f232b77__p0001_r000_b1158
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0146 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0118 duplicates doc_6004e35ceb4c0814__p0001_r000_b0110
- '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1332 duplicates doc_aefcb4588f232b77__p0001_r000_b1120
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0963 duplicates doc_aefcb4588f232b77__p0001_r000_b0956
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1159 duplicates doc_aefcb4588f232b77__p0001_r000_b1135
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0074 duplicates doc_6004e35ceb4c0814__p0001_r000_b0054
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0255 duplicates doc_aefcb4588f232b77__p0001_r000_b0232
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1333 duplicates doc_aefcb4588f232b77__p0001_r000_b1121
- Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0082 duplicates doc_6004e35ceb4c0814__p0001_r000_b0069
- Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1331 duplicates doc_aefcb4588f232b77__p0001_r000_b1119

---

## ⚠️ Document: `106_2025_QH15_628717.doc`

**Document ID:** `doc_6004e35ceb4c0814`  
**File Type:** `doc`  
**Extraction Strategy:** `long_local`  
**Overall Status:** `WARNING`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.04s | Loaded '106_2025_QH15_628717.doc' (type=doc, size=499,712 bytes) |
| document_profiling | ✅ pass | 4.44s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 4.37s | Extracted 1274 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.03s | Structured 1274 blocks, 0 tables, 13 sections, 116 articles, 0 clauses |
| cleaning_validation | ⚠️ warning | 0.01s | 9 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.01s | 116 chunks (0 degraded) using strategy=long_local_structural |
| graph_building | ✅ pass | 0.01s | 246 nodes, 3849 edges (3604 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.00s | Tested 8 queries (vi) — 7 hit, 1 missed (hit rate 88%, avg 12.4 chunks/query) |  |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1274 |
| Coverage Score | 1.00 |
| Degraded Blocks | 9 |
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
| Total Edges | 3849 |
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
| ALIAS_OF Edges | 3604 |
| Cross-lang Queries Tested | 3 |
| Cross-lang Hit Rate | 100% |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0074 duplicates doc_6004e35ceb4c0814__p0001_r000_b0054
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0082 duplicates doc_6004e35ceb4c0814__p0001_r000_b0069
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0118 duplicates doc_6004e35ceb4c0814__p0001_r000_b0110
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0143 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0146 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0150 duplicates doc_6004e35ceb4c0814__p0001_r000_b0134
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0767 duplicates doc_6004e35ceb4c0814__p0001_r000_b0660
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b0849 duplicates doc_6004e35ceb4c0814__p0001_r000_b0660
- ⚠️ Duplicate block detected: block_id=doc_6004e35ceb4c0814__p0001_r000_b1064 duplicates doc_6004e35ceb4c0814__p0001_r000_b0826
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
| document_profiling | ✅ pass | 0.72s | Strategy: long_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 5.21s | Extracted 1347 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.04s | Structured 1347 blocks, 0 tables, 41 sections, 220 articles, 0 clauses |
| cleaning_validation | ⚠️ warning | 0.01s | 11 warnings, 0 issues. Coverage: 1.00 |
| chunking | ✅ pass | 0.03s | 220 chunks (0 degraded) using strategy=long_local_structural |
| graph_building | ✅ pass | 0.02s | 482 nodes, 6527 edges (6046 ALIAS_OF) |
| retrieval_smoke_test | ✅ pass | 0.01s | Tested 8 queries (vi) — 7 hit, 1 missed (hit rate 88%, avg 12.6 chunks/query) |  |

### Extraction Metrics

| Metric | Value |
| --- | --- |
| Pages (source) | 0 |
| Pages (extracted) | 1 |
| Blocks | 1347 |
| Coverage Score | 1.00 |
| Degraded Blocks | 11 |
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
| Total Edges | 6527 |
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
| ALIAS_OF Edges | 6046 |
| Cross-lang Queries Tested | 3 |
| Cross-lang Hit Rate | 100% |

### Warnings

- ⚠️ '.doc' format: table topology cannot be reliably preserved with text extraction. Convert to .docx for full table support.
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0255 duplicates doc_aefcb4588f232b77__p0001_r000_b0232
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b0963 duplicates doc_aefcb4588f232b77__p0001_r000_b0956
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1159 duplicates doc_aefcb4588f232b77__p0001_r000_b1135
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1182 duplicates doc_aefcb4588f232b77__p0001_r000_b1158
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1183 duplicates doc_aefcb4588f232b77__p0001_r000_b1135
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1328 duplicates doc_aefcb4588f232b77__p0001_r000_b1116
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1329 duplicates doc_aefcb4588f232b77__p0001_r000_b1117
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1330 duplicates doc_aefcb4588f232b77__p0001_r000_b1118
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1331 duplicates doc_aefcb4588f232b77__p0001_r000_b1119
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1332 duplicates doc_aefcb4588f232b77__p0001_r000_b1120
- ⚠️ Duplicate block detected: block_id=doc_aefcb4588f232b77__p0001_r000_b1333 duplicates doc_aefcb4588f232b77__p0001_r000_b1121
- ⚠️ No results for query: 'khoản'

---
