# MVP Scope — LexAI / ULKA

---

## Trong phạm vi MVP (Beta)

| Capability | Status | Ghi chú |
|---|---|---|
| Legal situation analysis (6 domains) | ✅ | dat_dai, lao_dong, gia_dinh, dan_su, hop_dong, hanh_chinh |
| Domain classification (tiếng Việt có dấu) | ✅ | Keyword scoring, <10ms |
| Domain classification (không dấu) | ✅ | `_VI_INDICATORS_NODIAC` |
| Evidence status extraction | ✅ | PRESENT / MISSING / UNKNOWN |
| MongoDB Vector Search (law chunks) | ✅ | chunk_embedding_index, 384-dim cosine |
| Hybrid retrieval fusion | ✅ | Vector + BM25 + Graph + Behavior |
| LLM reasoning (OpenAI tool-calling) | ✅ | Fallback to deterministic nếu LLM unavailable |
| OutputValidator (contradiction removal) | ✅ | Land certificate + post-mediation detection |
| Context-aware action templates | ✅ | Post-mediation dat_dai switch |
| Template recommendations | ✅ | template_embedding_index |
| Risk recommendations | ✅ | risk_embedding_index |
| Similar cases (demo fallback) | ⚠️ | is_demo=True vì thiếu case_embedding_index |
| Evidence gap detection | ✅ | EvidenceGapEngine |
| Clause coach | ✅ | Contract clause analysis |
| Session memory (24h TTL) | ✅ | MongoDB conversation_sessions |
| Cross-session user memory | ✅ | user_memory collection, no TTL |
| Analysis history | ✅ | localStorage + backend sync |
| Admin upload (global docs) | ✅ | is_global=True pipeline |
| QA automation (365 tests) | ✅ | pytest full suite |
| Benchmark (30 queries) | ✅ | scripts/benchmark_retrieval.py |
| Release gate | ✅ | scripts/qa_release_gate.py |
| React frontend (user) | ✅ | 20+ pages |
| React admin panel | ✅ | Upload, jobs, stats |

---

## Ngoài phạm vi (Out of Scope)

| Capability | Lý do | Khi nào |
|---|---|---|
| Similar cases vector search (thật) | Atlas M0 limit — 3 FTS indexes đã đủ | Sau khi upgrade Atlas M10+ |
| Lawyer-in-the-loop review | Scope MVP | Roadmap mid-term |
| Court/procedure automation | Scope MVP | Roadmap long-term |
| Multilingual (English legal) | Scope MVP | Roadmap |
| Contract upload + processing | Scope MVP | Roadmap near-term |
| Legal advice guarantee | Không thể và không nên — AI không phải luật sư | Không bao giờ |
| GA deployment | Infra blocker (case_embedding_index) | Sau Atlas upgrade |

---

## Beta vs GA

| Capability | Beta | GA |
|---|---|---|
| Domain classification | ✅ 96.6% accuracy | ✅ Same |
| Law chunk retrieval | ✅ Vector search thật | ✅ Same |
| Similar cases | ⚠️ Demo fallback | ✅ Real vector search |
| Fallback/demo rate | ❌ 100% | ✅ ≤30% |
| Manual QA | ✅ 15/15 | ✅ Same |
| Automated tests | ✅ 365/365 | ✅ Same |
| Beta gate | ✅ PASS | — |
| GA gate | — | Pending Atlas upgrade |
| Load test (≥10 concurrent users) | ❌ Not done | ✅ Required |

---

## Gì không thuộc phạm vi dự thi này

1. **Không thay thế luật sư** — LexAI là tool hỗ trợ, không phải tư vấn pháp lý chính thức
2. **Không đảm bảo kết quả pháp lý** — AI có thể sai, người dùng cần verify với chuyên gia
3. **Không cover toàn bộ hệ thống pháp luật** — 6 domains phổ biến nhất với người dùng thông thường

---

## Định nghĩa "MVP Done"

MVP được coi là **hoàn thành** khi:
- ✅ 365/365 tests pass
- ✅ Top-1 domain accuracy ≥85% (đạt 96.6%)
- ✅ Cross-domain error = 0%
- ✅ Manual QA 15/15 pass
- ✅ Beta gate PASS
- ✅ OutputValidator chặn contradiction (no sổ đỏ re-suggestion)
- ✅ Post-mediation fix (no UBND mediation re-suggestion)
- ✅ Demo fallback có is_demo label (transparency)
