# Deep Audit v2 — LexAI / ULKA
**Ngày:** 2026-05-29 | **Reviewer:** Claude Code  
**Scope:** Production-readiness, user journeys, AI accuracy, retention, test coverage

---

## A. Những điểm audit trước đã đúng

1. **P0-1 (possessive phrase)** — `_POSSESSIVE_AFTER` list + `_status_for_occurrence()` đã fix đúng. "Sổ đỏ của tôi" → PRESENT.
2. **P0-2 (LLM instruction)** — `LEGAL_SYSTEM_PROMPT` đã có đoạn cứng "TUYỆT ĐỐI không viết cần thu thập" với status=PRESENT. Đúng hướng.
3. **P0-3 (filter)** — `filter_contradictory_recommendations()` + `_is_supplement_action()` đang chạy tốt, đã cover các verb thông dụng.
4. **Session store** — MongoDB 24h TTL session với history + law_type_preferences đủ cho multi-turn.
5. **Reflection agent** — Tier-1 regex + Tier-2 LLM non-blocking (daemon thread) — thiết kế đúng, không block response.
6. **Admin global doc** — `is_global=True` + `{$or: [{user_id}, {is_global: true}]}` filter — đúng isolation model.
7. **Evidence engine** — `EvidenceGapAnalysis.to_dict()` có đầy đủ 4 nhóm (present/missing/uncertain/contradicted), `coverage_score` logic hợp lý.
8. **Test suite cơ bản** — 261 tests pass, có test possessive, alias, filter, recommendation guard.

---

## B. Những điểm audit trước còn thiếu

### B-1: Cross-module contradiction (BUG NGHIÊM TRỌNG NHẤT)
`evidence_context` được tính **độc lập** ở:
- `orchestrator.py` line 190 (Stage 1)
- `situation_analyzer.py` (analyze() method)
- `recommendation_routes.py` (NBA endpoint — không tính, dùng `body.recommended_actions` raw)
- `risk_analysis_service.py` (tính lại từ đầu)

→ Kết quả: User nói "tôi có sổ đỏ" ở Analyze, nhưng NBA sidebar vẫn gợi ý "thu thập sổ đỏ". **Người dùng thật sẽ nghi ngờ toàn bộ hệ thống.**

### B-2: Demo injection vô điều kiện
`retrieval_routes.py` lines 595-606 inject case cứng **bất kể** vector search có kết quả tốt hay không. Nếu user hỏi về đất đai nhưng AI trả về "vụ tranh chấp ly hôn điển hình" → **confusion hoàn toàn**.

### B-3: Không có output validator
Sau khi LLM generate `full_assessment`, không có bước nào kiểm tra xem text có chứa "cần thu thập sổ đỏ" khi sổ đỏ=PRESENT. Prompt instruction có thể bị ignore nếu LLM temperature cao hoặc context dài.

### B-4: NBA không nhận `session_id`
`NextBestActionRequest` chưa có `session_id` field → không thể load evidence_snapshot → NBA luôn compute từ đầu, dẫn đến contradiction với Analyze session.

### B-5: CONTRADICTED clarification quá generic
`_build_recommendations()` line 281: `"Làm rõ tình trạng X: bạn đang giữ bản gốc, bản sao hay tài liệu đã bị mất?"` — câu hỏi này áp dụng cho tất cả evidence type, không có ngữ cảnh cụ thể (sổ đỏ vs hợp đồng lao động vs giấy khai sinh có context rất khác nhau).

### B-6: Thiếu test cho journey đa bước
Không có test nào mô phỏng multi-turn: Turn 1 (có sổ đỏ) → Turn 2 (NBA không được gợi ý thu thập sổ đỏ). Chỉ test unit isolate.

### B-7: Frontend không truyền session_id sang NBA
`Dashboard.tsx` / `EvidenceGap.tsx` khi gọi `getNextBestActions()` không gắn `session_id` vào request body, dù API có field này.

### B-8: RiskAnalysisService không dùng evidence_context từ session
`risk_analysis_service.py` tự chạy `EvidenceGapDetector()` từ đầu, không nhận evidence_context đã tính từ orchestrator.

### B-9: Thiếu confidence threshold cho retrieval
`retrieval_routes.py` không có ngưỡng tối thiểu cho `vector_score` khi quyết định fallback. Nếu top score = 0.2 (rất yếu) vẫn trả về kết quả như bình thường → hallucination risk cao.

### B-10: Không có cơ chế phục hồi niềm tin
Nếu AI trả lời sai 1 lần, không có UI nào cho user feedback "sai" → AI không học, user rời đi.

---

## C. User Journey Audit chi tiết

### Journey 1 — Tranh chấp đất, đã có sổ đỏ
```
Step 1: User nhập "Tôi đã có sổ đỏ, hàng xóm lấn 50cm đất"
        → Orchestrator Stage 1: evidence_context.land_certificate = PRESENT ✅
        → Stage 5 LLM: System prompt có PRESENT instruction ✅
        → Full assessment: thường OK

Step 2: User xem Evidence Gap tab
        → EvidenceGap gọi /analysis/evidence-gap độc lập
        → Tính lại evidence_context từ đầu
        → Nếu situation phrase khác 1 chút → có thể ra kết quả khác ⚠️

Step 3: User bấm NBA chip "Chuẩn bị hồ sơ"
        → NBA không có session_id → recompute evidence từ situation text
        → recommended_actions trong body = [] (không được fill)
        → NBA trả về generic actions, có thể bao gồm "thu thập sổ đỏ" ❌ BUG

Step 4: User hỏi tiếp "Cần làm gì trước?"
        → Multi-turn: session_ctx.history có turn 1
        → Nhưng evidence_snapshot KHÔNG được lưu vào session ❌
        → LLM không biết context "đã có sổ đỏ" từ turn 1 ← phải dựa vào history text
        → Nếu history context đủ dài: OK; nếu bị truncate: lỗi

Step 5: User bấm "Lưu phân tích"
        → Gọi saveAnalysis() → localStorage + backend /history ✅
        → Nhưng saved item không có evidence_status ⚠️
        → Khi load lại history, không có context về "đã có sổ đỏ"

Step 6: User về Dashboard
        → Dashboard NBA widget gọi /recommendations/next-best-actions
        → Body.situation = "" (empty, không có prefill) → NBA generic ⚠️
```

**Kết luận Journey 1:** Bước 3 là bug nghiêm trọng nhất. User sẽ thấy AI mâu thuẫn chính nó. Điểm dừng rời đi: bước 3.

---

### Journey 2 — Chưa có sổ đỏ, mua đất giấy tay
```
Step 1: "Tôi mua đất giấy tay từ 2010, chưa có sổ đỏ"
        → evidence_context: land_certificate = MISSING, transfer_document = PRESENT ✅
        → Recommendations: "Bổ sung Sổ đỏ/GCNQSDĐ" ✅

Step 2: Evidence Gap page
        → Hiển thị đúng: sổ đỏ = MISSING, giấy mua bán = PRESENT ✅

Step 3: User hỏi "Có thể đứng tên sổ đỏ không?"
        → Multi-turn: session có history ✅
        → LLM trả lời về thủ tục kê khai, đăng ký lần đầu ✅

Step 4: Similar Cases
        → Vector search: nếu có data → OK; nếu không → demo case inject ⚠️
        → Demo case "tranh chấp thừa kế" inject dù user hỏi về "mua đất giấy tay" ❌

Step 5: Timeline
        → Stage detection: "chưa có sổ đỏ" → stage = "pre_dispute" ✅
        → Deadlines: hỗ trợ tốt ✅
```

**Kết luận Journey 2:** Bước 4 inject case sai domain. Người dùng sẽ confused.

---

### Journey 3 — Bị sa thải trái phép
```
Step 1: "Công ty sa thải tôi không có lý do, không báo trước 30 ngày"
        → domain = lao_dong ✅
        → labor_contract status: UNCERTAIN (không nêu có hay không) ⚠️
        → LLM prompt: không biết user có hợp đồng lao động không → hỏi lại ✅

Step 2: User trả lời "tôi có hợp đồng lao động của tôi"
        → Turn 2: evidence_context tính lại: labor_contract = PRESENT ✅
        → Nhưng evidence_snapshot từ turn 1 không được update → turn 2 phải re-extract ✅ (OK vì text mới)

Step 3: NBA: "Nộp đơn khiếu nại lên Sở LĐTBXH"
        → Action URL: /actions?type=khieu-nai-lao-dong ✅ nếu frontend xử lý
        → Prefill context có situation text ✅

Step 4: Risk Analysis
        → RiskAnalysisService.analyze() độc lập: tính lại từ đầu ⚠️
        → strength_indicators check keywords trong situation text ✅ (dùng keyword, không vector)
        → "Có hợp đồng lao động" được detect nếu user nhắc lại ✅
```

**Kết luận Journey 3:** Tương đối ổn nếu user nhắc lại context. Vấn đề: user không nên phải nhắc lại.

---

### Journey 4 — Ly hôn, tranh chấp quyền nuôi con
```
Step 1: "Vợ chồng ly hôn, con 18 tháng tuổi, vợ muốn giành quyền nuôi"
        → domain = gia_dinh ✅
        → evidence: marriage_certificate = UNCERTAIN, birth_certificate = UNCERTAIN
        → LLM: giải thích Điều 81 LHN&GĐ 2014, ưu tiên mẹ với con < 36 tháng ✅

Step 2: User hỏi tiếp "Chồng tôi có thể kiện lại không?"
        → Multi-turn ✅
        → LLM nhớ: con 18 tháng, đang hỏi về quyền nuôi ✅
        → Context window: 20 turns max → OK

Step 3: Similar Cases
        → domain = gia_dinh → inject cases_pool[0] (custody case) ✅ trúng domain
        → Nhưng inject vô điều kiện dù vector search đã có kết quả tốt ⚠️

Step 4: Contract Analysis (user upload thỏa thuận ly hôn)
        → Upload file → pipeline 8 stages → embed
        → Contract page: phân tích điều khoản ✅
        → Nhưng không link với session "đang ly hôn" ❌ → user phải nhập lại context

Step 5: Export
        → Save button → localStorage + backend ✅
        → Download JSON → có ✅
        → PDF export → KHÔNG CÓ ❌ (người dùng cần in ra để nộp tòa)
```

**Kết luận Journey 4:** Thiếu PDF export là deal-breaker với user ly hôn cần in hồ sơ. Journey 4 bước 4 mất context hoàn toàn.

---

### Journey 5 — Đọc hợp đồng thuê nhà trước khi ký
```
Step 1: User upload PDF hợp đồng thuê nhà
        → Admin pipeline → embed → chunk → MongoDB ✅ (nếu pipeline OK)
        → Nhưng user thường không phải admin ⚠️
        → User phải dùng /documents/upload-file (user route) ← phân biệt rõ ràng chưa?

Step 2: Contract page: phân tích điều khoản rủi ro
        → CONTRACT_ANALYSIS_PROMPT: tốt, có 6 phần ✅
        → Output: điểm tuân thủ 0-100 ✅
        → Nhưng "thiếu điều khoản" có thể mâu thuẫn nếu điều khoản đó đã có trong PDF

Step 3: User hỏi "Điều khoản phạt 2 tháng tiền cọc có hợp lệ không?"
        → Analyze page: context shift từ contract sang general legal ⚠️
        → Không có cầu nối giữa Contract page và Analyze page ❌

Step 4: User muốn sửa điều khoản
        → Không có "Đề xuất sửa điều khoản cụ thể" action ❌
        → Không có "So sánh với điều khoản mẫu" action ❌

Step 5: Clause Coach
        → Tốt hơn: user paste điều khoản cụ thể → get advice ✅
        → Nhưng user phải copy-paste thủ công từ PDF ❌
```

**Kết luận Journey 5:** Workflow upload → analyze → question → modify bị đứt gãy hoàn toàn ở bước 3.

---

### Journey 6 — Người dùng quay lại sau 1 tuần
```
Step 1: User mở lại web sau 7 ngày
        → Session MongoDB đã expire (24h TTL) ❌
        → User memory (UserMemory no TTL) vẫn còn ✅
        → Dashboard: không tóm tắt "tuần trước bạn đang hỏi về đất đai" ❌

Step 2: User xem History
        → localStorage có items ✅
        → Backend /history sync ✅
        → Nhưng không có "tiếp tục từ lần trước" button ❌

Step 3: User bấm history item cũ
        → Load JSON analysis ✅
        → Không có "Phân tích lại" hoặc "Hỏi tiếp" từ context cũ ❌

Step 4: User nhập lại situation
        → Phải nhập lại toàn bộ từ đầu ❌
        → UserMemory có occupation/name nhưng không có situation summary trong prompt ← thực ra có, qua SituationRecord
        → Nhưng SituationRecord chỉ có 1-sentence summary, không đủ để tiếp tục
```

**Kết luận Journey 6:** Retention gap lớn. User quay lại sẽ cảm thấy phải bắt đầu lại từ đầu.

---

### Journey 7 — Người dùng mobile (cảm nhận UX)
```
Step 1: Sidebar navigation: 15+ items → mobile phải scroll nhiều ⚠️
Step 2: Analyze page: textarea input → OK trên mobile
Step 3: Evidence Gap: bảng nhiều cột → overflow trên mobile nhỏ ⚠️
Step 4: Similar Cases: card layout → OK
Step 5: Export JSON: file download → mobile không mở được dễ ⚠️
```

---

### Journey 8 — Người dùng không hiểu pháp luật (first-time user)
```
Step 1: Landing → Dashboard: không có onboarding ❌
        → User không biết bắt đầu từ đâu
        → Không có "Bắt đầu với tình huống của bạn" wizard

Step 2: User thử Analyze: nhập "tôi bị thiệt thòi"
        → Query quá ngắn / mơ hồ
        → Hệ thống cần hỏi lại nhưng: hỏi lại gì? ⚠️
        → Không có guided question flow

Step 3: User không hiểu "Vị thế pháp lý: Mạnh" nghĩa là gì
        → Không có tooltip hoặc giải thích ⚠️

Step 4: User thấy "Độ phủ chứng cứ: 33%" → không biết phải làm gì
        → Không có step-by-step guide từ coverage score ⚠️
```

**Kết luận Journey 8:** First-time user experience = D (không ổn với người không biết pháp luật).

---

### Journey 9 — Người dùng upload tài liệu cá nhân
```
Step 1: Documents page → Upload button ✅
Step 2: Upload PDF → trigger 8-stage pipeline ✅ (nếu backend healthy)
Step 3: Wait for processing → job status polling ✅
Step 4: Document processed → tìm kiếm có include doc này không? ← CẦN XÁC NHẬN
Step 5: Analyze với situation liên quan → có dùng user doc không?
        → Nếu is_global=False + user_id match → ✅ nhưng user không biết điều này
        → Không có UI feedback "đang dùng tài liệu của bạn" ⚠️
```

---

### Journey 10 — Admin upload luật mới
```
Step 1: Admin login → /admin/login ✅
Step 2: Upload file .doc → /admin/documents/upload ✅
Step 3: Job processing → AdminJobs page polling ✅
Step 4: Document indexed → is_global=True → tất cả user query sẽ thấy ✅
Step 5: Verify: user query liên quan → kết quả include doc mới
        → Không có "test query" tool trong admin panel ⚠️
```

---

## D. Output → Action Consistency Audit

| Output Type | CTA có không? | CTA đúng ngữ cảnh? | CTA dùng context cũ? | Bug? |
|---|---|---|---|---|
| AI Answer (Analyze) | ✅ NBA chips | ✅ thường đúng | ❌ không có session_id | B-4 |
| Evidence Gap | ✅ recommendations list | ⚠️ đôi khi mâu thuẫn | ❌ tính độc lập | B-1 |
| Risk Analysis | ⚠️ chỉ text | ❌ không có CTA button | ❌ tính độc lập | B-8 |
| Similar Cases | ⚠️ "Xem chi tiết" | ⚠️ đôi khi sai domain | N/A | B-2 |
| Law Search | ✅ "Phân tích với luật này" | ✅ | ❌ | - |
| Contract Analysis | ⚠️ chỉ text recommendations | ❌ không có "Sửa điều khoản" | ❌ | J5-S3 |
| NBA chips | ✅ navigate + prefill | ✅ | ❌ | B-4 |
| History item | ✅ "Download JSON" | ⚠️ không có "Tiếp tục" | ❌ | J6-S3 |
| Dashboard digest | ✅ links | ✅ | ❌ | - |
| Timeline deadlines | ✅ dates | ✅ | ❌ | - |
| Compliance radar | ⚠️ score only | ❌ không action button | ❌ | - |

**Critical dead actions:**
1. Risk Analysis → không có "Tạo kế hoạch giảm thiểu rủi ro" button
2. Contract Analysis → không có "Tạo đơn yêu cầu sửa điều khoản" 
3. Evidence Gap contradictions → clarification question generic, không có "Giải thích thêm" flow
4. History item → không có "Hỏi tiếp từ đây"
5. Coverage score thấp → không có "Xem checklist cần làm"

**Sai ngữ cảnh nghiêm trọng:**
- NBA gợi ý "Thu thập sổ đỏ" khi evidence = PRESENT (confirmed bug)
- Similar Cases inject "ly hôn" case khi user hỏi về "sa thải" (domain mismatch)

---

## E. Real User Retention Scorecard

| Tiêu chí | Điểm (1-10) | Lý do |
|---|---|---|
| First impression | 6 | UI đẹp nhưng quá nhiều tính năng, không rõ bắt đầu từ đâu |
| Hiểu web giúp gì | 5 | Tagline thiếu, không có landing page giải thích |
| Biết bắt đầu từ đâu | 4 | Sidebar 15 items, không có "bắt đầu tại đây" |
| Tin tưởng câu trả lời AI | 6 | Trích dẫn luật OK, nhưng mâu thuẫn giữa modules giảm niềm tin |
| Tin tưởng tài liệu gợi ý | 5 | Demo cases inject sai domain → user nghi ngờ |
| Rõ ràng action tiếp theo | 4 | Nhiều output chỉ có text, không có CTA button |
| Tốc độ phản hồi cảm nhận | 7 | Backend ổn, nhưng Evidence Gap load riêng làm double wait |
| Khả năng dùng lại lần sau | 4 | Session expire 24h, không có "tiếp tục từ lần trước" |
| Khả năng upload tài liệu | 5 | Có nhưng không rõ tài liệu đó được dùng ở đâu |
| Trả tiền nếu commercial | 3 | Chưa đủ trust, hay bị mâu thuẫn |
| **Tổng** | **4.9/10** | |

**Lý do người dùng ở lại:**
- UI dark mode đẹp, professional
- Trích dẫn luật Việt Nam cụ thể (Điều X, Luật Y)
- Evidence gap analysis concept hay (nếu không bị bug)
- Multi-turn conversation nhớ context trong session

**Lý do người dùng rời đi:**
1. AI nói "có sổ đỏ" nhưng gợi ý "xin cấp sổ đỏ" → mất tin hoàn toàn
2. Không biết bắt đầu từ đâu
3. Session hết → phải nhập lại từ đầu
4. Không có PDF export để in ra
5. Similar Cases sai domain gây bối rối

**Kết luận thẳng:**
- **Chưa đủ tốt** để mời người dùng thật. Cần fix bug mâu thuẫn B-1/B-4 trước.
- Trong 5 phút đầu: user sẽ hiểu "đây là AI tư vấn pháp lý". Nhưng sau lần AI mâu thuẫn đầu tiên → rời đi.
- Cơ chế phục hồi niềm tin: **không có** (chỉ có "Lưu", không có "Báo sai").
- Module demo-nhất: **Similar Cases** (inject hardcoded cases) và **Dashboard** (generic widgets).

---

## F. AI Accuracy Hardening Plan

### F-1: Intent Detection
**Hiện tại:** `QueryPlanner` dùng keyword scoring (deterministic, <10ms)  
**Vấn đề:** Câu "tôi bị thiệt thòi" → domain = general (đúng nhưng không hữu ích)  
**Fix:** Thêm clarifying question trigger: nếu `domain_confidence < 0.4` → prompt LLM "Hỏi 1 câu để xác định domain"

### F-2: User State Extraction (QUAN TRỌNG NHẤT)
**Hiện tại:** Mỗi module extract từ text riêng  
**Cần:** Structured `user_state` JSON, compute 1 lần, share across:
```json
{
  "domain": "dat_dai",
  "session_id": "s_abc",
  "evidence_status": {
    "land_certificate": "PRESENT",
    "payment_proof": "PRESENT",
    "transfer_document": "UNCERTAIN"
  },
  "user_role": "land_owner",
  "dispute_stage": "neighbor_encroachment",
  "desired_action": "resolve_dispute",
  "known_facts": ["đã có sổ đỏ", "hàng xóm lấn 50cm"],
  "missing_facts": [],
  "contradictions": [],
  "computed_at": "2026-05-29T10:00:00",
  "session_turn": 1
}
```
**Lưu vào:** `conversation_sessions.evidence_snapshot` (MongoDB, per session_id)

### F-3: Retrieval Query Rewrite
**Hiện tại:** `plan.query_variants` = 2-4 variants từ keyword expansion  
**Vấn đề:** Không loại bỏ stopwords, không handle sai chính tả, không expand domain-specific terms  
**Fix:** 
- Normalize input: strip diacritics → search cả dạng có/không dấu
- Expand: "sổ đỏ" → search cả "GCNQSDĐ", "giấy chứng nhận quyền sử dụng đất"
- Rewrite: nếu query có "của tôi" → remove possessive để search tốt hơn

### F-4: Retrieval Filtering
**Hiện tại:** `top_score` không được check trước khi trả kết quả  
**Fix:** 
```python
if top_score < 0.35:
    # Warning: low confidence retrieval
    add_warning("Không tìm thấy văn bản luật cụ thể, đang dùng kiến thức tổng hợp")
if top_score < 0.20:
    # Fallback only
    use_deterministic_only = True
```

### F-5: Hybrid Search Calibration
**Hiện tại:** Vector(0.45) + BM25(0.20) + Graph(0.25) + Behavior(0.10)  
**Vấn đề:** BM25 weight 0.20 quá thấp cho queries ngắn (<5 từ)  
**Fix:** Dynamic weight: nếu query ngắn (< 5 từ) → BM25 weight tăng lên 0.35, vector giảm xuống 0.30

### F-6: Citation Grounding
**Hiện tại:** `is_grounded = True` nếu có bất kỳ law chunk nào  
**Vấn đề:** Có thể có 1 chunk irrelevant nhưng vẫn báo grounded  
**Fix:** `is_grounded = (top_score > 0.45 AND len(relevant_laws) >= 2)`

### F-7: Citation Validation
**Hiện tại:** Không có  
**Cần:** Sau khi LLM generate, extract "Điều X Luật Y" → check xem có trong retrieved chunks không  
**Pattern:** `r"Điều\s+\d+[a-z]?\s+Luật\s+\w+"` → lookup in law_chunks → nếu không tìm thấy → add "(Kiến thức luật chung — khuyến nghị xác minh)"

### F-8: Recommendation Filtering (đã có, cần mạnh hơn)
**Hiện tại:** `filter_contradictory_recommendations()` ở evidence_gap_engine  
**Thiếu:** Không apply khi LLM generate `recommended_actions` trong `full_assessment` text  
**Fix:** OutputValidator check toàn bộ text output, không chỉ list

### F-9: Output Contradiction Detection
```python
class OutputValidator:
    _SUPPLEMENT_VERBS = ["cần thu thập", "bổ sung", "nộp thêm", "xin cấp lần đầu", "chưa có"]
    
    def validate_text(self, text: str, present_evidence: List[EvidenceAssessment]) -> str:
        """Rewrite output text: replace supplement suggestions for PRESENT items."""
        for item in present_evidence:
            for alias in item.aliases + [item.title]:
                for verb in self._SUPPLEMENT_VERBS:
                    pattern = f"{verb}.*?{alias}"
                    if re.search(pattern, text, re.IGNORECASE):
                        # Flag for review or rewrite
                        text = text + f"\n[Lưu ý: {item.title} đã được xác nhận là PRESENT]"
        return text
```

### F-10: Clarifying Question Policy
**Hiện tại:** LLM tự quyết định hỏi hay không  
**Cần:** Explicit rule:
- domain_confidence < 0.4 → hỏi 1 câu xác định domain
- present_evidence = [] AND missing_evidence > 3 → hỏi 1 câu về evidence nào có
- CONTRADICTED items > 0 → hỏi cụ thể từng item theo `_CONTRADICTION_CLARIFICATIONS`

### F-11: Fallback Response khi không đủ data
**Hiện tại:** Deterministic fallback có nhưng generic  
**Cần:** Fallback message phải:
1. Acknowledge: "Chưa tìm thấy văn bản luật cụ thể trong cơ sở dữ liệu"
2. General guidance dựa trên domain
3. CTA: "Tham khảo luật sư" hoặc "Xem điều luật liên quan"

### F-12: Regression Test cho Hallucination
**Bắt buộc** (xem mục H):
- "Tôi đã có sổ đỏ" → không có "cần thu thập sổ đỏ" trong bất kỳ output nào
- "Tôi đã hòa giải ở xã" → next action phải là "khởi kiện" không phải "hòa giải"

---

## G. Cross-module Context Sharing Design

### G-1: Architecture hiện tại (bị phá vỡ)
```
User Query
    │
    ├─ Orchestrator ─────────────── compute evidence_context (A)
    ├─ EvidenceGapDetector ──────── compute evidence_context (B) ← B ≠ A
    ├─ SituationAnalyzer ────────── compute evidence_context (C) ← C ≠ A
    ├─ RiskAnalysisService ──────── compute evidence_context (D) ← D ≠ A  
    └─ NBA endpoint ─────────────── no evidence_context at all (E)
```

### G-2: Architecture đề xuất (Single Source of Truth)
```
User Query
    │
    ▼
Orchestrator Stage 1
    → compute evidence_context ONCE
    → structured user_state JSON
    │
    ▼
MongoDB: session_store.evidence_snapshot ← persist
    │
    ├─ EvidenceGapDetector ── load from session_id → augment
    ├─ SituationAnalyzer ──── load from session_id → filter recommendations
    ├─ RiskAnalysisService ── load from session_id → use present_evidence for strengths
    └─ NBA endpoint ─────────── load from session_id → filter contradictions
```

### G-3: Implementation plan (file-by-file)

**Step 1: `src/memory/session_store.py`**
```python
@dataclass
class SessionContext:
    # ... existing fields ...
    evidence_snapshot: Optional[Dict[str, Any]] = None   # NEW
    evidence_domain: Optional[str] = None                 # NEW
    evidence_updated_at: Optional[str] = None             # NEW

def update_evidence_snapshot(self, session_id, user_id, evidence_snapshot, domain):
    self.sessions.update_one(
        {"session_id": session_id, "user_id": user_id},
        {"$set": {
            "evidence_snapshot": evidence_snapshot,
            "evidence_domain": domain,
            "evidence_updated_at": _now(),
            "last_active": _now(),
        }},
        upsert=True,
    )
```

**Step 2: `src/engine/orchestrator.py` Stage 7**
```python
# After save_context():
try:
    self._session_store.update_evidence_snapshot(
        session_id=sid, user_id=user_id,
        evidence_snapshot=evidence_context.to_dict(),
        domain=plan.detected_domain,
    )
except Exception as exc:
    logger.debug("evidence snapshot save failed: %s", exc)
```

**Step 3: `src/api/recommendation_routes.py` NBA endpoint**
```python
class NextBestActionRequest(BaseModel):
    # ... existing ...
    session_id: Optional[str] = None  # NEW

# In endpoint:
effective_recommended_actions = body.recommended_actions
if body.session_id:
    try:
        _ss = SessionStore()
        _sctx = _ss.load_context(body.session_id, user_id)
        if _sctx.evidence_snapshot:
            present_ev = _sctx.evidence_snapshot.get("present_evidence", [])
            if present_ev:
                effective_recommended_actions = filter_contradictory_recommendations(
                    body.recommended_actions, present_ev
                )
    except Exception as _e:
        logger.debug("NBA evidence load failed: %s", _e)
```

**Step 4: Frontend — truyền session_id vào NBA call**
```typescript
// api.ts getNextBestActions() — thêm session_id param
export async function getNextBestActions(params: {
  situation: string;
  session_id?: string;  // NEW
  // ... other params
}): Promise<NextBestActionOut[]>

// EvidenceGap.tsx, Analyze.tsx — truyền sessionId
const actions = await getNextBestActions({
  situation,
  session_id: currentSessionId,  // NEW
  ...
});
```

---

## H. Test Suite Design

### H-A: Unit Tests (hiện có + cần thêm)

#### H-A-1: Evidence extraction (đã có, cần thêm)
```python
# tests/evidence/test_evidence_extractor.py — THÊM:

def test_no_diacritics_labor_contract():
    """'hop dong lao dong cua toi' → labor_contract = PRESENT"""
    facts = aggregate_evidence_facts(
        extract_evidence_facts("hop dong lao dong cua toi bi vi pham", domain="lao_dong")
    )
    assert facts["labor_contract"].status == PRESENT

def test_contradicted_photo_only():
    """'có bản photo sổ đỏ nhưng mất bản gốc' → CONTRADICTED"""
    result = _status("tôi chỉ có bản photo sổ đỏ, bản gốc đã bị mất", "land_certificate")
    assert result == CONTRADICTED

def test_multi_domain_single_text():
    """Text có cả đất đai và lao động → extract đúng cho domain được chọn"""
    facts_land = aggregate_evidence_facts(
        extract_evidence_facts("tôi có sổ đỏ và hợp đồng lao động", domain="dat_dai")
    )
    assert facts_land["land_certificate"].status == PRESENT

def test_typo_tolerance():
    """'so doo cua toi' (typo) → không crash, UNCERTAIN OK"""
    result = _status("so doo cua toi bi tranh chap", "land_certificate")
    assert result in (PRESENT, UNCERTAIN)  # không crash
```

#### H-A-2: Recommendation filter (đã có, cần thêm)
```python
# tests/evidence/test_evidence_recommendation_guard.py — THÊM:

def test_filter_does_not_remove_valid_actions():
    """Filter không được xóa action không liên quan đến present evidence"""
    present = [EvidenceAssessment(evidence_id="land_certificate", title="Sổ đỏ/GCNQSDĐ", ...)]
    actions = [
        "Bổ sung Sổ đỏ/GCNQSDĐ",  # should be replaced
        "Nộp đơn khiếu nại lên UBND",  # should stay
        "Chuẩn bị biên bản tranh chấp",  # should stay
    ]
    filtered = filter_contradictory_recommendations(actions, present)
    assert not any("Bổ sung Sổ đỏ" in a for a in filtered)
    assert any("khiếu nại" in a for a in filtered)
    assert any("biên bản" in a for a in filtered)

def test_filter_handles_empty_present():
    """Empty present evidence → filter returns all unchanged"""
    actions = ["Thu thập sổ đỏ", "Nộp đơn"]
    filtered = filter_contradictory_recommendations(actions, [])
    assert filtered == actions

def test_filter_handles_synonyms():
    """Filter phát hiện synonym: 'GCNQSDĐ' khi present có 'Sổ đỏ/GCNQSDĐ'"""
    present = [EvidenceAssessment(evidence_id="land_certificate", 
                                   title="Sổ đỏ/GCNQSDĐ",
                                   aliases=["sổ đỏ", "gcn qsdđ", "giấy chứng nhận"],
                                   ...)]
    actions = ["Xin cấp GCNQSDĐ lần đầu"]
    filtered = filter_contradictory_recommendations(actions, present)
    assert not any("Xin cấp" in a and "GCNQSDĐ" in a for a in filtered)
```

#### H-A-3: Output validator (cần tạo mới)
```python
# tests/engine/test_output_validator.py — TOÀN BỘ FILE MỚI:

from src.engine.output_validator import OutputValidator
from src.evidence.evidence_schemas import EvidenceAssessment, PRESENT

def _present_item(evidence_id, title, aliases=None):
    return EvidenceAssessment(
        evidence_id=evidence_id, title=title, category="title",
        domain="dat_dai", priority="high", status=PRESENT,
        confidence=0.9, aliases=aliases or []
    )

class TestOutputValidator:
    def test_actions_no_conflict(self):
        v = OutputValidator()
        present = [_present_item("land_certificate", "Sổ đỏ/GCNQSDĐ", ["sổ đỏ"])]
        actions = ["Chuẩn bị hồ sơ khởi kiện", "Nộp đơn lên UBND"]
        result = v.validate(actions, type("EC", (), {"present_evidence": present})())
        assert result == actions

    def test_actions_suppress_supplement_for_present(self):
        v = OutputValidator()
        present = [_present_item("land_certificate", "Sổ đỏ/GCNQSDĐ", ["sổ đỏ"])]
        actions = ["Thu thập sổ đỏ", "Xin cấp giấy chứng nhận lần đầu", "Nộp đơn"]
        result = v.validate(actions, type("EC", (), {"present_evidence": present})())
        assert not any("Thu thập sổ đỏ" in a for a in result)
        assert any("Nộp đơn" in a for a in result)

    def test_no_evidence_context_passthrough(self):
        v = OutputValidator()
        actions = ["Thu thập sổ đỏ"]
        result = v.validate(actions, None)
        assert result == actions
```

---

### H-B: Integration Tests

#### H-B-1: Analyze → Evidence Gap → NBA consistency
```python
# tests/integration/test_cross_module_consistency.py — FILE MỚI

from fastapi.testclient import TestClient
from src.api.app import create_app

def test_analyze_evidence_nba_consistency():
    """
    Golden test: user nói có sổ đỏ → analyze → NBA không gợi ý thu thập sổ đỏ
    """
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    
    with TestClient(app) as client:
        headers = {"X-User-ID": "cross_module_test_user"}
        
        # Step 1: Analyze
        resp1 = client.post("/intelligence/analyze", headers=headers, json={
            "situation": "Tôi đã có sổ đỏ, hàng xóm lấn 50cm đất của tôi",
            "user_role": "nguyen_don",
            "law_type": "dat_dai",
        })
        assert resp1.status_code == 200
        session_id = resp1.json().get("session_id") or resp1.json().get("trace_id")
        
        # Step 2: NBA — must not suggest collecting sổ đỏ
        resp2 = client.post("/recommendations/next-best-actions", headers=headers, json={
            "situation": "Tôi đã có sổ đỏ, hàng xóm lấn 50cm đất của tôi",
            "session_id": session_id,
            "domain": "dat_dai",
            "recommended_actions": [],
        })
        assert resp2.status_code == 200
        nba_items = resp2.json()
        
        # Critical: no action should suggest collecting sổ đỏ
        all_action_text = " ".join([
            item.get("title", "") + " " + item.get("description", "")
            for item in nba_items
        ]).lower()
        
        assert "xin cấp sổ đỏ lần đầu" not in all_action_text
        assert "thu thập sổ đỏ" not in all_action_text


def test_evidence_gap_consistent_with_analyze():
    """Evidence Gap API cho cùng situation phải cho kết quả nhất quán với Analyze"""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    
    with TestClient(app) as client:
        headers = {"X-User-ID": "eg_consistency_user"}
        situation = "Hợp đồng lao động của tôi bị công ty vi phạm, họ sa thải không báo trước"
        
        resp = client.post("/analysis/evidence-gap", headers=headers, json={
            "situation": situation,
            "domain": "lao_dong",
            "facts": [],
        })
        assert resp.status_code == 200
        body = resp.json()
        
        present_ids = {item["evidence_id"] for item in body["present_evidence"]}
        missing_ids = {item["evidence_id"] for item in body["missing_evidence"]}
        
        # labor_contract phải PRESENT (possessive + "của tôi")
        assert "labor_contract" in present_ids
        assert "labor_contract" not in missing_ids
```

#### H-B-2: Multi-turn session test
```python
def test_multi_turn_maintains_evidence_context():
    """Turn 1 có sổ đỏ → Turn 2 AI không hỏi lại về sổ đỏ"""
    # Requires real MongoDB or mock session store
    # ... implementation
    pass
```

---

### H-C: E2E Test Cases (Golden 50)

```python
# tests/e2e/golden_cases.py — FILE MỚI

GOLDEN_CASES = [
    # ── Đất đai ──────────────────────────────────────────────────────────────
    {
        "id": "G01",
        "input": "Tôi đã có sổ đỏ, hàng xóm lấn 50cm",
        "domain": "dat_dai",
        "expected_present": ["land_certificate"],
        "expected_missing": [],
        "expected_no_recommend": ["xin cấp sổ đỏ", "thu thập sổ đỏ"],
    },
    {
        "id": "G02",
        "input": "Sổ đỏ của tôi bị hàng xóm tranh chấp",
        "domain": "dat_dai",
        "expected_present": ["land_certificate"],
        "expected_missing": [],
    },
    {
        "id": "G03",
        "input": "Tôi có GCN QSDĐ",
        "domain": "dat_dai",
        "expected_present": ["land_certificate"],
    },
    {
        "id": "G04",
        "input": "Tôi chưa có sổ đỏ",
        "domain": "dat_dai",
        "expected_missing": ["land_certificate"],
        "expected_present": [],
    },
    {
        "id": "G05",
        "input": "Tôi có bản photo sổ đỏ nhưng mất bản gốc",
        "domain": "dat_dai",
        "expected_status": {"land_certificate": "CONTRADICTED"},
        "expected_question": True,  # phải hỏi lại
    },
    {
        "id": "G06",
        "input": "toi co so do va bien lai chuyen khoan",  # không dấu
        "domain": "dat_dai",
        "expected_present": ["land_certificate", "payment_proof"],
    },
    {
        "id": "G07",
        "input": "bìa hồng đứng tên tôi bị hàng xóm chiếm",
        "domain": "dat_dai",
        "expected_present": ["land_certificate"],
    },
    {
        "id": "G08",
        "input": "Mua đất 2010 chưa có sổ đỏ, giấy tay viết tay",
        "domain": "dat_dai",
        "expected_missing": ["land_certificate"],
        "expected_present": ["transfer_document"],
    },
    {
        "id": "G09",
        "input": "Gia đình tôi có sổ đỏ nhưng anh trai đang giữ",
        "domain": "dat_dai",
        "expected_status": {"land_certificate": "CONTRADICTED"},
    },
    {
        "id": "G10",
        "input": "Đất của tôi, tôi đã thanh toán đầy đủ qua chuyển khoản",
        "domain": "dat_dai",
        "expected_present": ["payment_proof"],
    },

    # ── Lao động ─────────────────────────────────────────────────────────────
    {
        "id": "G11",
        "input": "Công ty sa thải tôi không lý do, không báo trước",
        "domain": "lao_dong",
        "expected_missing": ["labor_contract"],  # chưa nêu có
    },
    {
        "id": "G12",
        "input": "Hợp đồng lao động của tôi bị vi phạm",
        "domain": "lao_dong",
        "expected_present": ["labor_contract"],
    },
    {
        "id": "G13",
        "input": "Tôi là bên cho thuê, hợp đồng thuê nhà đã ký 2 năm",
        "domain": "hop_dong",
        "expected_role": "lessor",
        "expected_present": ["rental_contract"],
    },
    {
        "id": "G14",
        "input": "Tôi là bên thuê, hợp đồng chưa ký",
        "domain": "hop_dong",
        "expected_role": "lessee",
        "expected_missing": ["rental_contract"],
    },
    {
        "id": "G15",
        "input": "Bị sa thải vì lý do thai sản",
        "domain": "lao_dong",
        "expected_warning": ["bảo vệ thai sản", "Bộ luật Lao động"],
    },
    {
        "id": "G16",
        "input": "hop dong lao dong cua toi bi cong ty vi pham",  # không dấu
        "domain": "lao_dong",
        "expected_present": ["labor_contract"],
    },
    {
        "id": "G17",
        "input": "Không ký hợp đồng lao động nhưng làm việc 3 năm",
        "domain": "lao_dong",
        "expected_status": {"labor_contract": "MISSING"},
        "expected_recommend": ["hợp đồng miệng", "bằng chứng"],
    },
    {
        "id": "G18",
        "input": "BHXH của tôi đang bị công ty nợ",
        "domain": "lao_dong",
        "expected_present": ["social_insurance"],
    },

    # ── Hôn nhân / Gia đình ─────────────────────────────────────────────────
    {
        "id": "G19",
        "input": "Vợ chồng ly hôn, con 18 tháng, vợ muốn nuôi con",
        "domain": "gia_dinh",
        "expected_law": ["Điều 81", "Luật Hôn nhân"],
    },
    {
        "id": "G20",
        "input": "Giấy đăng ký kết hôn của chúng tôi bị mất",
        "domain": "gia_dinh",
        "expected_status": {"marriage_certificate": "CONTRADICTED"},
    },
    {
        "id": "G21",
        "input": "Tôi đã hòa giải ở xã nhưng không thành",
        "domain": "dat_dai",
        "expected_next_action": ["khởi kiện", "nộp đơn tòa án"],  # không được suggest "hòa giải"
        "expected_no_action": ["hòa giải tại UBND xã"],
    },
    {
        "id": "G22",
        "input": "Hợp đồng đã ký 3 tháng trước",
        "domain": "hop_dong",
        "expected_no_action": ["ký hợp đồng", "cần có hợp đồng"],
    },

    # ── Câu mâu thuẫn ─────────────────────────────────────────────────────────
    {
        "id": "G23",
        "input": "Tôi có sổ đỏ nhưng không có sổ đỏ",
        "domain": "dat_dai",
        "expected_status": {"land_certificate": "CONTRADICTED"},
    },
    {
        "id": "G24",
        "input": "Vừa có vừa không có hợp đồng",
        "domain": "hop_dong",
        "expected_clarification": True,
    },

    # ── Câu thiếu thông tin ────────────────────────────────────────────────────
    {
        "id": "G25",
        "input": "tôi bị thiệt thòi",
        "expected_domain_confidence_low": True,
        "expected_clarifying_question": True,
    },
    {
        "id": "G26",
        "input": "tranh chấp đất",
        "domain": "dat_dai",
        "expected_clarifying_question": True,  # thiếu chi tiết
    },

    # ── Câu dài phức tạp ──────────────────────────────────────────────────────
    {
        "id": "G27",
        "input": "Tôi mua đất từ năm 2010 theo giấy tay viết tay có người làm chứng, đã thanh toán đầy đủ qua tay, đến 2015 mới làm sổ đỏ, nhưng sổ đỏ đứng tên người bán vì khi đó chưa chuyển nhượng chính thức, nay muốn kiện đòi lại đất",
        "domain": "dat_dai",
        "expected_present": ["transfer_document", "payment_proof"],
        "expected_contradictions": ["land_certificate"],
    },

    # ── Đổi ý ở câu tiếp theo ─────────────────────────────────────────────────
    {
        "id": "G28_turn1",
        "input": "Tôi chưa có sổ đỏ",
        "expected_missing": ["land_certificate"],
    },
    {
        "id": "G28_turn2",
        "input": "À thực ra tôi có sổ đỏ rồi, nhầm",
        "expected_present": ["land_certificate"],
        "expected_missing": [],
        "note": "User đổi ý — phải re-extract từ turn mới, không cached",
    },

    # ── Multi-domain ─────────────────────────────────────────────────────────
    {
        "id": "G29",
        "input": "Tranh chấp đất giữa vợ chồng sau ly hôn",
        "expected_domains": ["dat_dai", "gia_dinh"],
        "note": "Multi-domain — system nên detect cả hai",
    },

    # ── Sai chính tả ─────────────────────────────────────────────────────────
    {
        "id": "G30",
        "input": "tôi có sổ đõ cua toi",  # "đỏ" → "đõ"
        "expected_present": ["land_certificate"],
        "note": "Typo tolerance — có thể UNCERTAIN nhưng không MISSING",
    },

    # ── Role detection ─────────────────────────────────────────────────────────
    {
        "id": "G31",
        "input": "Tôi là chủ đất, người thuê không chịu trả nhà",
        "expected_role": "landlord",
        "expected_domain": "hop_dong",
    },
    {
        "id": "G32",
        "input": "Tôi là người lao động bị sa thải",
        "expected_role": "employee",
    },
    {
        "id": "G33",
        "input": "Công ty tôi đang bị người lao động kiện",
        "expected_role": "employer",
    },

    # ── Citation test ──────────────────────────────────────────────────────────
    {
        "id": "G34",
        "input": "Quyền sử dụng đất theo luật đất đai",
        "expected_citation_pattern": r"Điều\s+\d+.*Luật Đất đai",
    },
    {
        "id": "G35",
        "input": "Nghĩa vụ cấp dưỡng sau ly hôn",
        "expected_citation_pattern": r"Điều\s+\d+.*Luật Hôn nhân",
    },

    # ── Hòa giải / khởi kiện flow ────────────────────────────────────────────
    {
        "id": "G36",
        "input": "Chưa hòa giải, đang bắt đầu tranh chấp",
        "expected_recommend": ["hòa giải tại UBND"],
    },
    {
        "id": "G37",
        "input": "Đã hòa giải tại UBND xã không thành",
        "expected_recommend": ["khởi kiện tòa án"],
        "expected_no_recommend": ["hòa giải"],
    },
    {
        "id": "G38",
        "input": "Đã khởi kiện rồi, đang chờ tòa",
        "expected_stage": "litigation",
        "expected_recommend": ["chuẩn bị hồ sơ", "thuê luật sư"],
    },

    # ── Tiếng Anh ────────────────────────────────────────────────────────────
    {
        "id": "G39",
        "input": "I have the land certificate but my neighbor is encroaching",
        "expected_present": ["land_certificate"],
        "language": "en",
    },
    {
        "id": "G40",
        "input": "I was fired without notice",
        "expected_domain": "lao_dong",
        "language": "en",
    },

    # ── Chứng cứ điện tử ────────────────────────────────────────────────────
    {
        "id": "G41",
        "input": "Tôi có tin nhắn Zalo chứng minh đã thanh toán",
        "expected_present": ["payment_proof"],
        "note": "Chứng cứ điện tử = payment_proof nếu mention chuyển khoản/thanh toán",
    },

    # ── Thừa kế ─────────────────────────────────────────────────────────────
    {
        "id": "G42",
        "input": "Bố tôi mất không để lại di chúc, 3 anh em tranh chấp đất",
        "domain": "dan_su",
        "expected_missing": ["will"],
        "expected_present": [],
    },
    {
        "id": "G43",
        "input": "Di chúc của bố tôi bị anh trai giữ",
        "expected_status": {"will": "CONTRADICTED"},
    },

    # ── Hợp đồng thương mại ──────────────────────────────────────────────────
    {
        "id": "G44",
        "input": "Hợp đồng mua bán hàng hóa đã ký, bên mua không thanh toán",
        "domain": "hop_dong",
        "expected_present": ["sales_contract"],
        "expected_missing": ["payment_proof"],
    },

    # ── Doanh nghiệp ─────────────────────────────────────────────────────────
    {
        "id": "G45",
        "input": "Cổ đông thiểu số bị ép buộc bán cổ phần",
        "domain": "doanh_nghiep",
        "expected_warning": ["quyền cổ đông thiểu số"],
    },

    # ── Hành chính ─────────────────────────────────────────────────────────
    {
        "id": "G46",
        "input": "UBND ra quyết định thu hồi đất sai luật",
        "domain": "dat_dai",
        "expected_recommend": ["khiếu nại quyết định hành chính"],
    },

    # ── Tình huống khẩn cấp ─────────────────────────────────────────────────
    {
        "id": "G47",
        "input": "Ngày mai tòa xử, tôi chưa có luật sư",
        "expected_urgency": "cao",
        "expected_warning": ["thời hạn", "khẩn cấp"],
    },

    # ── Thời hiệu ────────────────────────────────────────────────────────────
    {
        "id": "G48",
        "input": "Tranh chấp đất từ năm 2010, 15 năm trước",
        "expected_warning": ["thời hiệu", "hết hạn"],
    },

    # ── Câu chào / small-talk ────────────────────────────────────────────────
    {
        "id": "G49",
        "input": "Xin chào",
        "expected_chitchat": True,
        "expected_no_domain": True,
    },
    {
        "id": "G50",
        "input": "Cảm ơn bạn rất nhiều",
        "expected_chitchat": True,
    },
]
```

---

### H-D: Regression Tests bắt buộc (phải pass trước khi deploy)

```python
# tests/regression/test_evidence_regression.py — FILE MỚI

REGRESSION_CASES = [
    # R01: PRESENT + no supplement recommend
    ("Tôi đã có sổ đỏ", "dat_dai", "land_certificate", "PRESENT"),
    # R02: Possessive = PRESENT
    ("Sổ đỏ của tôi bị tranh chấp", "dat_dai", "land_certificate", "PRESENT"),
    # R03: GCN QSDĐ alias
    ("Tôi có GCN QSDĐ", "dat_dai", "land_certificate", "PRESENT"),
    # R04: MISSING
    ("Tôi chưa có sổ đỏ", "dat_dai", "land_certificate", "MISSING"),
    # R05: Photo-only = CONTRADICTED
    ("Tôi chỉ có bản photo, mất bản gốc", "dat_dai", "land_certificate", "CONTRADICTED"),
    # R06: Labor contract possessive
    ("Hợp đồng lao động của tôi bị vi phạm", "lao_dong", "labor_contract", "PRESENT"),
    # R07: Marriage cert PRESENT
    ("Giấy đăng ký kết hôn của chúng tôi vẫn còn", "gia_dinh", "marriage_certificate", "PRESENT"),
    # R08: Already reconciled
    ("Đã hòa giải ở xã không thành", "dat_dai", None, None),
    # R09: Contract already signed
    ("Hợp đồng đã ký rồi", "hop_dong", None, None),
]

def test_regression_evidence_status():
    for situation, domain, evidence_id, expected_status in REGRESSION_CASES:
        if evidence_id is None:
            continue
        facts = aggregate_evidence_facts(
            extract_evidence_facts(situation, domain=domain)
        )
        if evidence_id in facts:
            assert facts[evidence_id].status == expected_status, \
                f"REGRESSION {situation!r}: {evidence_id} expected {expected_status} got {facts[evidence_id].status}"

def test_regression_no_supplement_for_present():
    """Bắt buộc: situation có sổ đỏ → recommendation không có 'thu thập sổ đỏ'"""
    from src.evidence.evidence_gap_engine import analyze_evidence_gap
    situations = [
        "Tôi đã có sổ đỏ, hàng xóm lấn đất",
        "Sổ đỏ của tôi bị tranh chấp",
        "GCN QSDĐ đứng tên tôi, đang tranh chấp",
    ]
    BAD_PATTERNS = ["xin cấp sổ đỏ", "thu thập sổ đỏ", "bổ sung sổ đỏ", "cần có sổ đỏ"]
    for s in situations:
        result = analyze_evidence_gap(s, "dat_dai")
        for rec in result.recommendations:
            for pat in BAD_PATTERNS:
                assert pat.lower() not in rec.lower(), \
                    f"REGRESSION: '{s}' got bad recommendation: '{rec}'"

def test_regression_reconciled_means_next_is_lawsuit():
    """Đã hòa giải không thành → recommend khởi kiện, không recommend hòa giải lại"""
    from src.evidence.evidence_gap_engine import analyze_evidence_gap
    result = analyze_evidence_gap(
        "Tôi đã hòa giải ở UBND xã nhưng không thành công", "dat_dai"
    )
    recs_lower = " ".join(result.recommendations).lower()
    assert "hòa giải tại ubnd" not in recs_lower or "không thành" in recs_lower
```

---

## I. Priority Fix Roadmap mới

### P0 — Fix ngay (blocking trust)

| ID | Tên | File | Độ khó | Thời gian |
|---|---|---|---|---|
| P0-A | NBA không mâu thuẫn với PRESENT evidence | `recommendation_routes.py` + `session_store.py` + `orchestrator.py` | M | 1 ngày |
| P0-B | Similar Cases: threshold gate cho demo injection | `retrieval_routes.py` lines 595-606 | S | 2 giờ |
| P0-C | Add regression tests R01-R09 vào CI | `tests/regression/` | S | 3 giờ |

**Acceptance criteria P0-A:**
- `test_analyze_evidence_nba_consistency()` pass
- "Tôi có sổ đỏ" → NBA không có string "thu thập sổ đỏ" trong bất kỳ title/description

**Acceptance criteria P0-B:**
- `top_score >= 0.45` → demo cases KHÔNG inject
- `top_score < 0.45 OR fallback_used` → demo cases inject như cũ

---

### P1 — Fix để dùng mượt (blocking retention)

| ID | Tên | File | Độ khó | Thời gian |
|---|---|---|---|---|
| P1-A | OutputValidator: check full_assessment text | `src/engine/output_validator.py` (new) | M | 4 giờ |
| P1-B | CONTRADICTED clarification per-type | `evidence_gap_engine.py` | S | 2 giờ |
| P1-C | Domain confidence → clarifying question | `orchestrator.py` Stage 1 | M | 4 giờ |
| P1-D | History item: "Hỏi tiếp từ đây" button | `frontend/AnalysisHistory.tsx` | S | 3 giờ |
| P1-E | Risk Analysis: nhận evidence_context | `risk_analysis_service.py` | M | 4 giờ |
| P1-F | Frontend: truyền session_id vào NBA call | `frontend/api.ts` + `Dashboard.tsx` + `EvidenceGap.tsx` | S | 2 giờ |

---

### P2 — Nâng cấp production-grade

| ID | Tên | File | Độ khó | Thời gian |
|---|---|---|---|---|
| P2-A | Structured user_state JSON persist đầy đủ | `session_store.py` mở rộng | L | 2 ngày |
| P2-B | Citation validation (Điều X Luật Y) | `orchestrator.py` Stage 7 | M | 1 ngày |
| P2-C | Dynamic BM25/vector weight theo query length | `retrieval_fusion.py` | M | 4 giờ |
| P2-D | Retrieval confidence warning | `orchestrator.py` + frontend | M | 1 ngày |
| P2-E | PDF export (Playwright/WeasyPrint) | backend + frontend | L | 3 ngày |
| P2-F | "Báo sai" feedback button | frontend + backend /feedback endpoint | M | 2 ngày |
| P2-G | Onboarding wizard (first-time user) | frontend new component | L | 3 ngày |
| P2-H | Golden test runner (50 cases) | `tests/e2e/golden_runner.py` | M | 2 ngày |

---

## J. Danh sách file cần sửa

### J-1: `src/memory/session_store.py`
**Lý do:** Thêm 3 field evidence_snapshot để share cross-module  
**Sửa gì:** Thêm fields vào `SessionContext` dataclass, thêm `update_evidence_snapshot()` method, update `load_context()` để restore 3 fields mới  
**Acceptance:** `update_evidence_snapshot()` → read back → 3 fields khớp  
**Test:** `tests/integration/test_cross_module_consistency.py::test_session_store_evidence_snapshot`

### J-2: `src/engine/orchestrator.py`
**Lý do:** Lưu evidence_snapshot vào session sau Stage 1 + wire OutputValidator  
**Sửa gì:** Stage 7: gọi `update_evidence_snapshot()`, import OutputValidator, validate `recommended_actions`  
**Acceptance:** Sau analyze, session có evidence_snapshot với đúng present_evidence  
**Test:** `test_analyze_evidence_nba_consistency()`

### J-3: `src/api/recommendation_routes.py`
**Lý do:** NBA endpoint phải load evidence từ session  
**Sửa gì:** Thêm `session_id: Optional[str]` vào `NextBestActionRequest`, thêm evidence load + filter trước khi build context  
**Acceptance:** NBA với session_id có sổ đỏ → không suggest thu thập sổ đỏ  
**Test:** `test_analyze_evidence_nba_consistency()`

### J-4: `src/api/retrieval_routes.py`
**Lý do:** Demo case injection không có threshold → sai domain  
**Sửa gì:** Lines 595-606: wrap trong `if fallback_used or top_score < 0.45:`  
**Acceptance:** vector_score=0.8 → không inject demo case  
**Test:** `tests/api/test_retrieval_similar_cases.py` (thêm threshold test)

### J-5: `src/evidence/evidence_gap_engine.py`
**Lý do:** CONTRADICTED clarification quá generic  
**Sửa gì:** Thêm `_CONTRADICTION_CLARIFICATIONS` dict + `_contradiction_clarification()` helper, update `_build_recommendations()`  
**Acceptance:** "sổ đỏ" CONTRADICTED → message về bản gốc/bản sao/người khác giữ  
**Test:** unit test `test_contradiction_clarification_per_type()`

### J-6: `src/engine/output_validator.py` (NEW FILE)
**Lý do:** Không có safety layer sau LLM generation  
**Sửa gì:** Tạo file mới, class `OutputValidator` với method `validate(actions, evidence_context)`  
**Acceptance:** actions có "thu thập sổ đỏ" + present="land_certificate" → action bị rewrite  
**Test:** `tests/engine/test_output_validator.py`

### J-7: `tests/api/test_evidence_gap_accuracy.py`
**Lý do:** Chỉ có 1 test, cần thêm T02-T04  
**Sửa gì:** Thêm 3 tests theo plan  
**Acceptance:** All 4 tests pass

### J-8: `tests/regression/test_evidence_regression.py` (NEW FILE)
**Lý do:** Không có regression suite  
**Sửa gì:** Tạo file mới với R01-R09  
**Acceptance:** All pass, thêm vào CI

### J-9: `frontend/src/lib/api.ts`
**Lý do:** `getNextBestActions()` không truyền `session_id`  
**Sửa gì:** Thêm `session_id?: string` vào params interface và request body  
**Acceptance:** NBA call có session_id trong body khi component truyền vào

### J-10: `frontend/src/pages/EvidenceGap.tsx` + `Dashboard.tsx`
**Lý do:** Không lấy / truyền session_id vào NBA call  
**Sửa gì:** Lấy session_id từ analysisContext hoặc localStorage, truyền vào getNextBestActions()  
**Acceptance:** Network request NBA có field `session_id` trong body

---

## K. Prompt cho AI/Codex implement P0

```
TASK: Fix P0 bugs in LexAI Legal AI system.
Priority: Zero hallucination — never recommend collecting evidence user already has.

SCOPE: P0 only. Do NOT refactor, rename, or move code outside the listed files.
Run tests after each group. Report file changed + reason + test result.

=== GROUP 1: session_store.py ===

File: src/memory/session_store.py

1. Add 3 optional fields to SessionContext dataclass (after existing fields):
   - evidence_snapshot: Optional[Dict[str, Any]] = None
   - evidence_domain: Optional[str] = None  
   - evidence_updated_at: Optional[str] = None

2. In load_context(): after loading from MongoDB, also restore these 3 fields from doc.

3. Add new method update_evidence_snapshot():
   def update_evidence_snapshot(self, session_id: str, user_id: str, 
                                 evidence_snapshot: Dict, domain: str) -> None:
       try:
           self.sessions.update_one(
               {"session_id": session_id, "user_id": user_id},
               {"$set": {
                   "evidence_snapshot": evidence_snapshot,
                   "evidence_domain": domain,
                   "evidence_updated_at": <call existing _now()>,
                   "last_active": <call existing _now()>,
               }},
               upsert=True,
           )
       except Exception as exc:
           logger.warning("update_evidence_snapshot failed: %s", exc)

Run: python -m pytest tests/ -q -x --tb=short
Expect: same pass count as before (no regression)

=== GROUP 2: orchestrator.py — evidence snapshot save ===

File: src/engine/orchestrator.py

Find the Stage 7 block where save_context() is called (around line 486).
AFTER the save_context() call, add:

    try:
        self._session_store.update_evidence_snapshot(
            session_id=sid,
            user_id=user_id,
            evidence_snapshot=evidence_context.to_dict(),
            domain=plan.detected_domain,
        )
    except Exception as exc:
        logger.debug("evidence snapshot save failed (non-fatal): %s", exc)

Do NOT change any other part of orchestrator.py.

Run: python -m pytest tests/ -q -x --tb=short
Expect: same pass count as before

=== GROUP 3: recommendation_routes.py — NBA session_id ===

File: src/api/recommendation_routes.py

1. Find class NextBestActionRequest. Add field after last existing field:
   session_id: Optional[str] = None

2. Find the recommend_next_best_actions endpoint function.
   Find where body.recommended_actions is used to build context.
   BEFORE that line, add:

   effective_recommended_actions = body.recommended_actions
   if body.session_id:
       try:
           from src.memory.session_store import SessionStore
           from src.evidence.evidence_gap_engine import filter_contradictory_recommendations
           _ss = SessionStore()
           _sctx = _ss.load_context(body.session_id, user_id)
           if _sctx and _sctx.evidence_snapshot:
               present_ev = _sctx.evidence_snapshot.get("present_evidence", [])
               if present_ev:
                   effective_recommended_actions = filter_contradictory_recommendations(
                       body.recommended_actions, present_ev
                   )
       except Exception as _e:
           logger.debug("NBA evidence snapshot load failed: %s", _e)

3. Replace body.recommended_actions with effective_recommended_actions
   ONLY in the NBA endpoint function body (not in type definitions).

Run: python -m pytest tests/ -q -x --tb=short
Expect: same pass count as before

=== GROUP 4: retrieval_routes.py — demo injection threshold ===

File: src/api/retrieval_routes.py

Find lines 595-607 (the demo injection block starting with:
"# Inject highly specialized fallback cases...")

Read current code:
    cases_pool = _FALLBACK_CASES_EN if query_language == "en" else _FALLBACK_CASES
    if query_language == "en":
        if domain == "lao_dong" and not any("severance" ...):
            raw.insert(0, cases_pool[1])
        elif domain in ("gia_dinh", "dan_su") and not any("custody" ...):
            raw.insert(0, cases_pool[0])
    else:
        if domain in ("gia_dinh", "dan_su") and not any("36 tháng" ...):
            raw.insert(0, cases_pool[0])
        elif domain == "lao_dong" and not any("sa thải" ...):
            raw.insert(0, cases_pool[1])

Add threshold gate AROUND the whole block:
    top_score = raw[0].get("vector_score", 0.0) if raw else 0.0
    if fallback_used or top_score < 0.45:
        cases_pool = _FALLBACK_CASES_EN if query_language == "en" else _FALLBACK_CASES
        if query_language == "en":
            ... (keep existing inner code unchanged)
        else:
            ... (keep existing inner code unchanged)

Run: python -m pytest tests/ -q -x --tb=short
Expect: same pass count as before

=== GROUP 5: New regression tests ===

File: tests/regression/test_evidence_regression.py  (CREATE NEW)

Create this file with content from Section H-D of the audit document.
Then run: python -m pytest tests/regression/ -q --tb=short
All tests must pass.

=== DONE CRITERIA ===
1. All 4 existing passes still pass (no regression)
2. test_regression_evidence_status() pass
3. test_regression_no_supplement_for_present() pass  
4. test_regression_reconciled_means_next_is_lawsuit() pass
5. (if MongoDB available): test_analyze_evidence_nba_consistency() pass

IMPORTANT RULES:
- Do NOT touch UI code in this P0 pass
- Do NOT change API response schema (fields can be added, not removed)
- Do NOT change existing test files (only add new ones)
- Do NOT use --no-verify or skip hooks
- Report: file changed, lines changed, test result after each group
```

---

*End of Deep Audit v2 — LexAI/ULKA*  
*Total estimated fix time: P0 = 1.5 ngày | P1 = 1.5 ngày | P2 = 8+ ngày*
