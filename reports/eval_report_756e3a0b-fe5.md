# Legal GraphRAG Pipeline Evaluation Report

**Run ID:** `756e3a0b-fe58-4d42-8f7f-42884c1e8c58`  
**Processing Version:** `0.1.0`  
**Started:** 2026-05-13T04:41:29.001964+00:00  
**Finished:** 2026-05-13T04:41:29.702365+00:00  
**Duration:** 0.70s  
**Overall Status:** ❌ `FAIL`

## Summary

| Metric | Value |
| --- | --- |
| Documents Processed | 2 |
| Passed | ✅ 0 |
| Warnings | ⚠️ 0 |
| Failed | ❌ 2 |

## ❌ Critical Failures

- No blocks extracted. Document may be empty, encrypted, or unsupported.
- No blocks extracted — document may be empty or unsupported.
- No blocks extracted. Document may be empty, encrypted, or unsupported.
- No blocks extracted — document may be empty or unsupported.

## ⚠️ Key Warnings

- chunk_set is empty; no retrieval test possible
- Could not extract text from '45_2019_QH14_333670.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- Could not extract text from '106_2025_QH15_628717.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- .doc file produced no text. File may be corrupt or binary-only.

## 💡 Recommendations

- Install extraction libraries: pip install pdfminer.six python-docx beautifulsoup4
- For OCR support: pip install pytesseract Pillow
- Some documents failed. Check logs in the output/logs/ directory.

---

## ❌ Document: `106_2025_QH15_628717.doc`

**Document ID:** `doc_6004e35ceb4c0814`  
**File Type:** `doc`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `FAIL`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.09s | Loaded '106_2025_QH15_628717.doc' (type=doc, size=499,712 bytes) |
| document_profiling | ⚠️ warning | 0.58s | Strategy: simple_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 0.00s | Extracted 0 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 0 blocks, 0 tables, 0 sections, 0 articles, 0 clauses |
| cleaning_validation | ❌ fail | 0.00s | 0 warnings, 1 issues. Coverage: 0.00 |
| chunking | ✅ pass | 0.00s | 0 chunks (0 degraded) using strategy=semantic |
| graph_building | ✅ pass | 0.00s | 1 nodes, 0 edges created |
| retrieval_smoke_test | ⚠️ warning | 0.00s | No chunks available for smoke test. |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 1 |
| Total Edges | 0 |
| Structural Edges | 0 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 0 |
| Queries with Results | 0 |
| Avg Result Count | 0.0 |

### Warnings

- ⚠️ Could not extract text from '106_2025_QH15_628717.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- ⚠️ .doc file produced no text. File may be corrupt or binary-only.
- ⚠️ Could not extract text from '106_2025_QH15_628717.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- ⚠️ chunk_set is empty; no retrieval test possible

### Critical Failures

- ❌ No blocks extracted. Document may be empty, encrypted, or unsupported.
- ❌ No blocks extracted — document may be empty or unsupported.

---

## ❌ Document: `45_2019_QH14_333670.doc`

**Document ID:** `doc_aefcb4588f232b77`  
**File Type:** `doc`  
**Extraction Strategy:** `simple_local`  
**Overall Status:** `FAIL`

### Stage Results

| Stage | Status | Duration | Summary |
| --- | --- | --- | --- |
| input_loading | ✅ pass | 0.00s | Loaded '45_2019_QH14_333670.doc' (type=doc, size=482,816 bytes) |
| document_profiling | ⚠️ warning | 0.00s | Strategy: simple_local | pages=0 | tables=False |
| extraction | ⚠️ warning | 0.00s | Extracted 0 blocks, 0 tables from 1 pages |
| canonical_structuring | ✅ pass | 0.00s | Structured 0 blocks, 0 tables, 0 sections, 0 articles, 0 clauses |
| cleaning_validation | ❌ fail | 0.00s | 0 warnings, 1 issues. Coverage: 0.00 |
| chunking | ✅ pass | 0.00s | 0 chunks (0 degraded) using strategy=semantic |
| graph_building | ✅ pass | 0.00s | 1 nodes, 0 edges created |
| retrieval_smoke_test | ⚠️ warning | 0.00s | No chunks available for smoke test. |

### Graph Metrics

| Metric | Value |
| --- | --- |
| Total Nodes | 1 |
| Total Edges | 0 |
| Structural Edges | 0 |
| Low Confidence Edges | 0 |
| Nodes by Type | {"Document": 1} |

### Retrieval Smoke Test

| Metric | Value |
| --- | --- |
| Queries Tested | 0 |
| Queries with Results | 0 |
| Avg Result Count | 0.0 |

### Warnings

- ⚠️ Could not extract text from '45_2019_QH14_333670.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- ⚠️ .doc file produced no text. File may be corrupt or binary-only.
- ⚠️ Could not extract text from '45_2019_QH14_333670.doc'. Install docx2txt (`pip install docx2txt`) or antiword (OS package) for .doc support.
- ⚠️ chunk_set is empty; no retrieval test possible

### Critical Failures

- ❌ No blocks extracted. Document may be empty, encrypted, or unsupported.
- ❌ No blocks extracted — document may be empty or unsupported.

---
