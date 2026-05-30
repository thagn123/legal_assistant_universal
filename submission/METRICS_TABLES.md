# Metrics Tables — LexAI / ULKA

Tổng hợp tất cả số liệu để dùng trong video và tài liệu.

---

## 1. Test Suite

| Suite | Tests | Status |
|---|---|---|
| Engine unit tests | ~120 | ✅ All pass |
| Evidence tests | ~60 | ✅ All pass |
| API tests | ~80 | ✅ All pass |
| S-05 regression (post-mediation) | 25 | ✅ All pass |
| Other (integration, validation) | ~80 | ✅ All pass |
| **Total** | **365** | **✅ 365/365 pass** |

---

## 2. Retrieval Benchmark

**Generated:** 2026-05-30T02:03:25Z  
**Mode:** http (live backend)  
**Queries:** 30 total (6 domains + general + edge cases)

| Metric | Value | Target | Status |
|---|---|---|---|
| Top-1 domain accuracy | **96.6%** (28/29) | ≥85% | ✅ |
| Top-3 domain accuracy | **96.6%** | ≥90% | ✅ |
| Cross-domain error | **0.0%** | 0% | ✅ |
| Empty rate | **0.0%** | 0% | ✅ |
| Avg top-1 score | **0.52** | ≥0.55 | ❌ infra |
| Fallback/demo rate | **100%** | ≤30% | ❌ infra |
| HTTP error count | **0** | 0 | ✅ |

---

## 3. Accuracy Progression

| Checkpoint | Queries Correct | Accuracy |
|---|---|---|
| Baseline (before patches) | 23/29 | 79.3% |
| After P1 (labor override) | 23/29 | 79.3% (no change — Q27 was already fixed) |
| After P2 | 28/29 | **96.6%** |

### P2 — 6 queries fixed

| Fix | Queries | Root Cause |
|---|---|---|
| P2-A: gia_dinh primary keywords | Q15, Q16, Q17 | dict ordering tie → dan_su wins |
| P2-B: hanh_chinh "khiếu nại" keyword | Q24, Q25 | hop_dong tie + empty fallback pool |
| P2-C: dat_dai no-diacritics aliases | Q26 | "so do" classified as English |

---

## 4. Manual QA

| Metric | Value |
|---|---|
| Total scenarios | 15 |
| Passed | 15 (sau retest S-05) |
| Failed | 0 |
| Blocked | 0 |
| P0 bugs found | 1 (B-S05-P0) — **fixed** |
| P1 issues | 1 (B-S13-P1 — domain label wrong, content correct) |

---

## 5. Release Gate

| Gate | Status |
|---|---|
| Beta release | ✅ **PASS_BETA** |
| GA release | ❌ **FAIL_GA** |

### Hard Gates (all pass)

| Gate | Status |
|---|---|
| HG-1: P0 contradictions = 0 | ✅ |
| HG-2: Forbidden phrases = 0 | ✅ |
| HG-3: API 500 errors = 0 | ✅ |
| HG-4: Demo labelling correct | ✅ |
| HG-5: Cross-domain error = 0% | ✅ |
| HG-6: Score threshold leak = 0 | ✅ |

### GA Blockers

| Blocker | Root Cause | Fix |
|---|---|---|
| `fallback_demo_rate = 100%` | Atlas M0: 3 vector index limit, `case_embedding_index` cannot be created | Upgrade Atlas M10+ |

---

## 6. MongoDB Index Status

| Index | Collection | Dimensions | Status |
|---|---|---|---|
| `chunk_embedding_index` | `chunks_vec` | 384 cosine | ✅ Active |
| `template_embedding_index` | `templates` | 384 cosine | ✅ Active |
| `risk_embedding_index` | `risks` | 384 cosine | ✅ Active |
| `case_embedding_index` | `legal_cases` | 384 cosine | ❌ Atlas M0 limit |
| `clause_embedding_index` | `contract_clauses` | 384 cosine | ❌ Atlas M0 limit |

---

## 7. S-05 Bug Metrics

| Metric | Before Fix | After Fix |
|---|---|---|
| Manual QA S-05 | ❌ FAIL | ✅ PASS |
| UBND mediation in post-mediation actions | YES (bug) | NO (fixed) |
| Court guidance in post-mediation actions | NO (missing) | YES |
| Regression tests | 0 | 25 |
| Total tests | 340 | **365** |
| Post-mediation signals detected | 0 | 16 phrases |
| No-diacritics variants covered | 0 | 8 phrases |

---

## 8. Retrieval Fusion Weights

| Signal | Weight | Method |
|---|---|---|
| Vector | 0.45 | MongoDB $vectorSearch, 384-dim cosine |
| Graph | 0.25 | BFS law-reference expansion |
| BM25 | 0.20 | TF keyword density ×20 |
| Behavior | 0.10 | Collaborative filter, decay rate 0.08 |
| **Total** | **1.00** | — |

---

## 9. Recommendation Ranker Weights

| Signal | Weight |
|---|---|
| Semantic (cosine similarity) | 0.35 |
| Graph centrality | 0.20 |
| Behavior history | 0.15 |
| Freshness (half-life 180 days) | 0.15 |
| Popularity | 0.10 |
| Accepted history | 0.05 |
| **Total** | **1.00** |

---

## 10. Performance Benchmarks

| Operation | Typical Latency |
|---|---|
| Stage 1: QueryPlanner | <10ms |
| Evidence extraction | <5ms |
| MongoDB $vectorSearch | ~50–200ms |
| BM25 scoring | <5ms |
| Full pipeline (no LLM) | ~200–500ms |
| Full pipeline (with LLM) | ~2000–8000ms (OpenAI latency) |
| Benchmark Q01 elapsed | 21,410ms (first cold start) |
| Benchmark Q02 elapsed | 181ms (warm) |
