# Video Storyboard — LexAI / ULKA

**Tổng thời gian:** 10:00  
**Resolution:** 1920×1080 (hoặc 1280×720 nếu máy yếu)  
**Font zoom:** 125% trong browser, 14pt+ trong terminal  

---

| # | Thời gian | Màn hình | Thao tác | Lời thoại tóm tắt | Screenshot cần |
|---|---|---|---|---|---|
| 1 | 0:00–0:10 | Dashboard hoặc trang chủ LexAI | Mở browser, vào `localhost:3000` | [Không nói, chỉ để logo và UI hiện] | ✅ `01_homepage.png` |
| 2 | 0:10–0:45 | Slide hoặc browser — giữ trang chủ | Không thao tác | Hook: bài toán người dân không biết thủ tục pháp lý + chatbot tự mâu thuẫn | — |
| 3 | 0:45–1:30 | Slide kiến trúc đơn giản (hoặc TECHNICAL_DOCUMENT.md mermaid) | Scroll/show diagram | Giới thiệu 3 điểm khác biệt: evidence, vector search, validate | ✅ `02_architecture_overview.png` |
| 4 | 1:30–1:45 | Trang `/analyze` — empty state | Mở tab mới, vào `/analyze` | "Bây giờ tôi sẽ demo trực tiếp..." | ✅ `03_analyze_empty.png` |
| 5 | 1:45–2:00 | `/analyze` — input box | Gõ: `Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?` | Đọc input | ✅ `04_demo1_input.png` |
| 6 | 2:00–2:30 | `/analyze` — loading | Click Phân tích, đợi response | "Hệ thống phải nhận ra tôi đã nói: tôi đã có sổ đỏ..." | — |
| 7 | 2:30–3:00 | `/analyze` — kết quả | Scroll đến phần domain detection + position | Chỉ vào domain: dat_dai, confidence | ✅ `05_demo1_domain.png` |
| 8 | 3:00–3:30 | `/analyze` — Recommended Actions | Zoom vào section recommended_actions | "Không có dòng nào gợi ý thu thập sổ đỏ..." | ✅ `06_demo1_actions_no_cert.png` |
| 9 | 3:30–4:00 | `/analyze` — Full Assessment | Scroll xuống full_assessment | Chỉ vào phần position_reasoning | ✅ `07_demo1_full_assessment.png` |
| 10 | 4:00–4:15 | `/analyze` — clear hoặc tab mới | Clear input hoặc mở tab mới | "Bây giờ case quan trọng nhất..." | — |
| 11 | 4:15–4:30 | `/analyze` — input box | Gõ: `Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.` | Đọc input, nhấn mạnh "đã hòa giải" | ✅ `08_demo2_input.png` |
| 12 | 4:30–5:00 | `/analyze` — loading | Click Phân tích | Giải thích bug cũ (lỗi P0 trong manual QA) | — |
| 13 | 5:00–5:30 | `/analyze` — Recommended Actions | Zoom vào section | Chỉ: "biên bản hòa giải không thành", "khởi kiện", "Tòa án nhân dân" | ✅ `09_demo2_actions_court.png` |
| 14 | 5:30–5:45 | `/analyze` — key_action | Scroll đến key_action trong full_assessment | Chỉ câu "bạn đã hoàn thành bước hòa giải bắt buộc" | ✅ `10_demo2_key_action.png` |
| 15 | 5:45–6:00 | `/analyze` — input box | Gõ: `Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng tôi không đồng ý. Tôi có thể làm được không?` | Đọc input | ✅ `11_demo3_input.png` |
| 16 | 6:00–6:30 | `/analyze` — loading + kết quả | Click Phân tích, đợi | Nói về case nhạy cảm — không được nói "không thể ly hôn" | — |
| 17 | 6:30–7:00 | `/analyze` — kết quả | Zoom vào full_assessment + recommended_actions | Chỉ: gia_dinh domain, quyền ly hôn đơn phương, nuôi con <36 tháng | ✅ `12_demo3_family_result.png` |
| 18 | 7:00–7:20 | TECHNICAL_DOCUMENT.md hoặc slide | Scroll qua system architecture Mermaid | Giải thích 7-stage pipeline | ✅ `13_architecture_diagram.png` |
| 19 | 7:20–7:45 | MongoDB Atlas hoặc slide collection schema | Mở Atlas console hoặc show screenshot | Chỉ collection chunks_vec, vector index | ✅ `14_mongodb_atlas_index.png` |
| 20 | 7:45–8:00 | VECTOR_SEARCH_AND_AGGREGATION.md | Scroll đến aggregation pipeline code | Đọc pipeline: $vectorSearch → $match score → $sort | ✅ `15_aggregation_pipeline.png` |
| 21 | 8:00–8:20 | Terminal | `python -m pytest tests/ -q --tb=no` | Chờ kết quả | ✅ `16_test_suite_365_pass.png` |
| 22 | 8:20–8:45 | `qa/retrieval_benchmark_report.md` | Mở file trong VS Code preview | Chỉ bảng Metrics vs Targets: 96.6%, 0%, 0% | ✅ `17_benchmark_96pct.png` |
| 23 | 8:45–9:15 | `qa/release_gate_report.md` | Mở file | Chỉ Beta PASS, GA FAIL, giải thích infra blocker | ✅ `18_release_gate_report.png` |
| 24 | 9:15–9:45 | Slide / text | Không thao tác | Impact: người dân, roadmap | — |
| 25 | 9:45–10:00 | Trang chủ LexAI | Quay về homepage | Kết thúc, cảm ơn | — |

---

## Zoom Guide

| Khi nào | Zoom vào đâu | Cách zoom |
|---|---|---|
| Demo 1 — actions | Section "Hành động được khuyến nghị" | Ctrl+= để phóng to, hoặc crop khi edit video |
| Demo 2 — actions | Tìm: "biên bản hòa giải không thành" | Highlight bằng chuột hoặc scroll chậm |
| Demo 2 — key_action | Phần "Bước ưu tiên nhất" | Pause 3 giây để giám khảo đọc |
| Benchmark | Bảng Metric / Target / Status | Zoom cột Status (✅/❌) |
| Release gate | Verdict: PASS_BETA / FAIL_GA | Để cursor nhấp nháy trên dòng PASS_BETA |
| Terminal | `365 passed in xx.xx s` | Phóng to font 16pt+ trước khi quay |

---

## Transition Notes

- **Segment 2→3:** Cut nhanh — không cần fade
- **Segment 3→4:** Mở browser tab mới — không cần giải thích
- **Segment 9→10:** "Bây giờ tôi sẽ thử case thứ hai — case phức tạp hơn"
- **Segment 13→15:** "Case thứ ba — nhạy cảm hơn về mặt nội dung"
- **Segment 17→21:** Cut sang terminal — "Và đây là kết quả kiểm thử tự động"

---

## Backup Plan (nếu backend không chạy được)

Nếu backend không start được khi quay:

1. Dùng file `qa/api_smoke_report.json` — có sample responses
2. Show screenshot đã chụp trước (từ SCREENSHOT_GUIDE)
3. Narrate qua output JSON trực tiếp trong terminal: `cat qa/api_smoke_report.json | python -m json.tool`
4. Cuối cùng: show file `qa/retrieval_benchmark_report.md` và `qa/release_gate_report.md` thay cho live demo
