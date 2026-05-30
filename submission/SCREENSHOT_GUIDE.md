# Screenshot Guide — LexAI / ULKA

**Tổng số ảnh cần:** 18  
**Thư mục lưu:** `submission/screenshots/`  
**Format:** PNG, 1920×1080 hoặc 1280×720  
**Font size:** Zoom browser 125%, terminal font 14pt+  

---

## Chuẩn bị trước khi chụp

1. Start backend: `python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001`
2. Start frontend: `cd "lexai-–-trợ-lý-pháp-lý-thông-minh UI" && npm run dev`
3. Mở browser tại `http://localhost:3000`
4. **Tắt notifications** trên Windows (Focus Assist / Do Not Disturb)
5. **Đóng taskbar** nếu muốn ảnh clean (auto-hide taskbar)
6. Zoom browser: Ctrl+= đến 125%

---

## Screenshot 01 — Dashboard / Homepage

**File:** `screenshots/01_homepage.png`  
**URL:** `http://localhost:3000` hoặc `http://localhost:3000/dashboard`  
**Thao tác:** Không thao tác gì, để trang load xong  
**Crop:** Toàn bộ viewport  
**Chứng minh:** Giao diện clean, professional, tiếng Việt  
**Caption:** "LexAI — Legal Intelligence Assistant. Dashboard với gợi ý proactive và tóm tắt."

---

## Screenshot 02 — Architecture Diagram

**File:** `screenshots/02_architecture.png`  
**Nguồn:** Mở `submission/TECHNICAL_DOCUMENT.md` trong VS Code → Cmd+Shift+V (Markdown Preview)  
**Thao tác:** Scroll đến section "3. System Architecture", mermaid diagram hiện ra  
**Crop:** Chỉ lấy phần diagram (flowchart)  
**Chứng minh:** 7-stage pipeline từ User → MongoDB → Response  
**Caption:** "7-stage Legal Intelligence Pipeline: QueryPlanner → EvidenceExtractor → RetrievalFusion → LLM → OutputValidator → Response."

---

## Screenshot 03 — Analyze Page (Empty State)

**File:** `screenshots/03_analyze_empty.png`  
**URL:** `http://localhost:3000/analyze`  
**Thao tác:** Trang mới, chưa nhập gì  
**Crop:** Toàn bộ page bao gồm input box  
**Chứng minh:** UI sạch, có placeholder text hướng dẫn người dùng  
**Caption:** "Trang phân tích tình huống pháp lý — nhập mô tả bằng tiếng Việt tự nhiên."

---

## Screenshot 04 — Demo 1 Input (Đất đai có sổ đỏ)

**File:** `screenshots/04_demo1_input.png`  
**URL:** `http://localhost:3000/analyze`  
**Thao tác:** Gõ vào input box:

```
Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?
```

**Crop:** Input box với text đã nhập, nút Phân tích  
**Chứng minh:** Input tự nhiên tiếng Việt  
**Caption:** "Demo 1: Người dùng đã có sổ đỏ — hệ thống phải nhận diện evidence status = PRESENT."

---

## Screenshot 05 — Demo 1 Result — Recommended Actions (KHÔNG có "thu thập sổ đỏ")

**File:** `screenshots/05_demo1_actions_clean.png`  
**Thao tác:** Sau khi nhấn Phân tích, đợi kết quả, scroll đến "Hành động được khuyến nghị"  
**Crop:** Phần recommended_actions — phải thấy rõ danh sách actions  
**Quan trọng:** Xác nhận **không có** dòng nào chứa "thu thập sổ đỏ", "xin cấp GCN", "làm sổ đỏ"  
**Caption:** "Recommended actions KHÔNG gợi ý thu thập sổ đỏ vì evidence status = PRESENT. OutputValidator đã lọc action mâu thuẫn."

---

## Screenshot 06 — Demo 1 — Domain + Evidence Status

**File:** `screenshots/06_demo1_domain_evidence.png`  
**Thao tác:** Scroll lên đầu result, tìm phần domain detection và position strength  
**Crop:** Domain badge "Đất đai", confidence %, position strength (Mạnh/Trung bình/Yếu)  
**Caption:** "Domain classifier: dat_dai. Evidence-grounded position assessment."

---

## Screenshot 07 — Demo 1 — Full Assessment

**File:** `screenshots/07_demo1_full_assessment.png`  
**Thao tác:** Scroll đến phần full_assessment  
**Crop:** Phần text full assessment (khoảng 3-5 dòng đầu)  
**Caption:** "Full assessment căn cứ vào evidence: vì đã có sổ đỏ, vị thế pháp lý mạnh."

---

## Screenshot 08 — Demo 2 Input (Hòa giải không thành)

**File:** `screenshots/08_demo2_input.png`  
**Thao tác:** Clear hoặc mở tab mới, gõ:

```
Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.
```

**Crop:** Input box với text  
**Caption:** "Demo 2: S-05 P0 scenario — 'đã hòa giải không thành'. Hệ thống cũ sẽ re-suggest hòa giải."

---

## Screenshot 09 — Demo 2 — Recommended Actions (Có "khởi kiện", "biên bản")

**File:** `screenshots/09_demo2_actions_court.png`  
**Thao tác:** Đợi kết quả, scroll đến recommended_actions  
**Crop:** Danh sách actions  
**Quan trọng:** Phải thấy ít nhất một trong: "biên bản hòa giải không thành", "khởi kiện", "Tòa án nhân dân"  
**Quan trọng:** Xác nhận **không có** "Nộp đơn yêu cầu hòa giải tại UBND"  
**Caption:** "Sau fix S-05: actions chuyển sang chuẩn bị hồ sơ khởi kiện — không re-suggest bước đã hoàn thành."

---

## Screenshot 10 — Demo 2 — Key Action (Court filing)

**File:** `screenshots/10_demo2_key_action.png`  
**Thao tác:** Scroll đến key_action trong full_assessment  
**Crop:** Câu "Bước ưu tiên nhất: chuẩn bị hồ sơ khởi kiện..."  
**Caption:** "Key action context-aware: nhận biết người dùng đã hoàn thành hòa giải → chuyển sang khởi kiện."

---

## Screenshot 11 — Demo 3 — Ly hôn đơn phương (Kết quả)

**File:** `screenshots/11_demo3_family.png`  
**Thao tác:** Nhập `Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng không đồng ý.` → đợi kết quả  
**Crop:** Domain badge (gia_dinh) + một phần full_assessment  
**Quan trọng:** Phải thấy "gia_dinh" domain, và không có câu "không thể ly hôn"  
**Caption:** "Demo 3: Case nhạy cảm — ly hôn đơn phương. Domain gia_dinh. Không có forbidden phrase 'không thể ly hôn'."

---

## Screenshot 12 — Release Gate — PASS_BETA

**File:** `screenshots/12_release_gate_pass_beta.png`  
**Nguồn:** Mở `qa/release_gate_report.md` trong VS Code Markdown Preview  
**Thao tác:** Scroll đến bảng Verdict  
**Crop:** Phần "Beta release: ✅ PASS_BETA" và "GA release: ❌ FAIL_GA"  
**Caption:** "Release gate tự động: Beta PASS. GA FAIL do infra blocker — case_embedding_index chưa tạo được."

---

## Screenshot 13 — Benchmark Report

**File:** `screenshots/13_benchmark_96pct.png`  
**Nguồn:** Mở `qa/retrieval_benchmark_report.md` trong VS Code preview  
**Crop:** Bảng "Metrics vs Targets" — phần top-1 96.6%, cross-domain 0%, empty 0%  
**Caption:** "Benchmark 30 queries: Top-1 accuracy 96.6%, cross-domain error 0%."

---

## Screenshot 14 — Terminal — 365 Tests Pass

**File:** `screenshots/14_test_suite_365.png`  
**Thao tác:** Mở terminal, chạy:
```
cd "c:\Users\Admin\OneDrive\Máy tính\Universal Legal Knowledge Assistant"
python -m pytest tests/ -q --tb=no
```
**Crop:** Dòng cuối: `365 passed in xx.xx s`  
**Font size:** 14pt+, zoom terminal 125%  
**Caption:** "Full test suite: 365/365 pass. Bao gồm 25 regression tests cho S-05 P0 fix."

---

## Screenshot 15 — MongoDB Atlas — Collections List

**File:** `screenshots/15_mongodb_collections.png`  
**Thao tác:** Mở MongoDB Atlas → Database → legal_knowledge_assistant → Collections  
**Crop:** List collections: chunks_vec, templates, risks, legal_cases, interactions, conversation_sessions, user_memory  
**Caption:** "MongoDB Atlas database: 9 collections. chunks_vec chứa law chunks với 384-dim embeddings."

---

## Screenshot 16 — MongoDB Atlas — Vector Search Index

**File:** `screenshots/16_mongodb_vector_index.png`  
**Thao tác:** Mở Atlas → chunks_vec → Search Indexes  
**Crop:** Index `chunk_embedding_index`, type vectorSearch, status Active  
**Caption:** "chunk_embedding_index: 384-dim cosine similarity trên chunks_vec."

---

## Screenshot 17 — MongoDB Sample Document

**File:** `screenshots/17_mongodb_sample_doc.png`  
**Thao tác:** Atlas → chunks_vec → Documents → click vào 1 document  
**Crop:** Document structure: chunk_id, content (50 chars), law_type, law_reference, embedding (hiện [0.023, -0.112, ...] — 384 dims), is_global  
**Caption:** "Law chunk document với 384-dim embedding, law_reference, is_global flag."

---

## Screenshot 18 — Aggregation Pipeline Code

**File:** `screenshots/18_aggregation_pipeline.png`  
**Nguồn:** Mở `submission/VECTOR_SEARCH_AND_AGGREGATION.md` trong VS Code  
**Crop:** Phần code aggregation pipeline section 4.1  
**Caption:** "MongoDB aggregation: $vectorSearch → $match score threshold → $sort → top-K results."

---

## Bonus Screenshots (nếu có thời gian)

### B1 — Evidence Gap Page

**File:** `screenshots/bonus_evidence_gap.png`  
**URL:** `http://localhost:3000/evidence-gap`  
**Caption:** "Evidence gap detection — nhận biết bằng chứng còn thiếu."

### B2 — Similar Cases với Demo Badge

**File:** `screenshots/bonus_similar_cases_demo.png`  
**URL:** `http://localhost:3000/similar-cases`  
**Caption:** "Similar cases với badge 'Ví dụ tham khảo' — transparent về demo fallback."

### B3 — Admin Upload Panel

**File:** `screenshots/bonus_admin_upload.png`  
**URL:** `http://localhost:3000/admin/documents`  
**Caption:** "Admin panel: upload legal documents để seed global knowledge base."

---

## Checklist trước khi nộp

- [ ] 14 ảnh bắt buộc (01–18 trừ bonus) đã chụp
- [ ] Tất cả ảnh có font đủ lớn để đọc được
- [ ] Demo 2 actions KHÔNG có "hòa giải tại UBND"
- [ ] Demo 2 actions CÓ "biên bản hòa giải không thành" hoặc "khởi kiện"
- [ ] Terminal screenshot hiện rõ "365 passed"
- [ ] Benchmark screenshot hiện rõ "96.6%"
- [ ] Release gate screenshot hiện rõ "PASS_BETA"
- [ ] MongoDB screenshot hiện collections hoặc index
