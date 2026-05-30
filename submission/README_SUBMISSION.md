# LexAI — Evidence-Grounded Legal AI Assistant for Vietnamese Citizens

> **Tagline:** Không chỉ trả lời — kiểm chứng, truy xuất và bảo vệ người dùng khỏi tư vấn pháp lý tự mâu thuẫn.

---

## Dự án

| Field | Value |
|---|---|
| **Tên dự án** | LexAI / ULKA — Universal Legal Knowledge Assistant |
| **Stack** | Python 3.11 · FastAPI · MongoDB Atlas · sentence-transformers · OpenAI API · React 19 + TypeScript + Vite + Tailwind |
| **Domain** | Pháp luật Việt Nam (đất đai, lao động, hôn nhân gia đình, dân sự, hợp đồng, hành chính) |
| **Ngôn ngữ hỗ trợ** | Tiếng Việt (có dấu + không dấu) |
| **Trạng thái** | Beta PASS · GA FAIL (1 infra blocker: Atlas M0 vector index limit) |

---

## Bài toán

Người dân Việt Nam thiếu khả năng tiếp cận tư vấn pháp lý đơn giản và đáng tin cậy. Chatbot pháp lý thông thường mắc hai lỗi nghiêm trọng:

1. **Tự mâu thuẫn với dữ kiện người dùng đã cung cấp** — người dùng nói "tôi đã có sổ đỏ" nhưng hệ thống vẫn gợi ý "thu thập sổ đỏ".
2. **Lặp lại bước đã hoàn thành** — người dùng nói "đã hòa giải không thành" nhưng action list vẫn khuyên đi hòa giải.

Đây không phải lỗi nhỏ — trong bối cảnh pháp lý, tư vấn sai có thể làm người dùng bỏ lỡ thời hiệu khởi kiện hoặc thực hiện sai thủ tục.

---

## Giải pháp

LexAI là một **Legal Intelligence Pipeline** gồm 7 giai đoạn:

```
Input → QueryPlanner → SessionLoader → RetrievalFusion → GraphExpander
      → LLM Reasoning → RecommendationRanker → OutputValidator → Response
```

Điểm khác biệt cốt lõi:
- **Evidence extraction** — nhận diện trạng thái bằng chứng từ câu hỏi (có/chưa có sổ đỏ, đã/chưa hòa giải)
- **OutputValidator** — loại bỏ hành động mâu thuẫn với evidence đã biết
- **Context-aware action templates** — với dat_dai post-mediation case, action list tự động chuyển từ "đi hòa giải" sang "chuẩn bị hồ sơ khởi kiện"
- **QA release gate** — tự động phát hiện blocker trước khi GA

---

## Key Features

| Feature | Mô tả |
|---|---|
| Legal situation analysis | Phân tích tình huống → domain → evidence status → legal strength |
| Evidence gap detection | Nhận diện bằng chứng còn thiếu, cần bổ sung |
| MongoDB Vector Search | Truy xuất law chunks bằng 384-dim cosine similarity |
| Hybrid retrieval fusion | Vector (0.45) + BM25 (0.20) + Graph (0.25) + Behavior (0.10) |
| Context-aware actions | Action list điều chỉnh theo trạng thái đã hoàn thành |
| Output validation | Lọc action tự mâu thuẫn với evidence người dùng đã cung cấp |
| Similar cases | Tìm case tương tự (demo fallback khi thiếu vector index) |
| QA automation | 365 tests · benchmark · release gate |
| No-diacritics support | Nhận diện domain kể cả khi gõ không dấu |

---

## MongoDB Usage

| Collection | Mục đích | Vector Index |
|---|---|---|
| `chunks_vec` | Law chunks với 384-dim embeddings | `chunk_embedding_index` ✅ |
| `templates` | Mẫu hợp đồng | `template_embedding_index` ✅ |
| `risks` | Legal risk patterns | `risk_embedding_index` ✅ |
| `legal_cases` | Similar cases | `case_embedding_index` ❌ (Atlas M0 limit) |
| `interactions` | User behavior log | — |
| `community_case_patterns` | Anonymized community patterns | — |

Aggregation Pipeline: domain filter → vector score projection → threshold filter → sort → rerank

---

## QA Results

| Metric | Value | Target | Status |
|---|---|---|---|
| Unit + integration tests | 365/365 | — | ✅ All pass |
| Top-1 domain accuracy | 96.6% (28/29) | ≥85% | ✅ |
| Top-3 domain accuracy | 96.6% | ≥90% | ✅ |
| Cross-domain error | 0.0% | 0% | ✅ |
| Empty rate | 0.0% | 0% | ✅ |
| Manual QA | 15/15 (sau retest S-05) | 15/15 | ✅ |
| Beta gate | **PASS** | — | ✅ |
| GA gate | FAIL (infra blocker) | — | ❌ |

---

## Links to Documentation

| File | Nội dung |
|---|---|
| [TECHNICAL_DOCUMENT.md](TECHNICAL_DOCUMENT.md) | Kiến trúc hệ thống, 7-stage pipeline, modules |
| [MONGODB_ARCHITECTURE.md](MONGODB_ARCHITECTURE.md) | Collections, indexes, schemas, ER diagram |
| [VECTOR_SEARCH_AND_AGGREGATION.md](VECTOR_SEARCH_AND_AGGREGATION.md) | Vector search + aggregation pipeline chi tiết |
| [VIDEO_DEMO_SCRIPT.md](VIDEO_DEMO_SCRIPT.md) | Kịch bản video 10 phút + lời thoại tiếng Việt |
| [VIDEO_STORYBOARD.md](VIDEO_STORYBOARD.md) | Bảng storyboard từng giây |
| [SCREENSHOT_GUIDE.md](SCREENSHOT_GUIDE.md) | Hướng dẫn chụp 18 ảnh cụ thể |
| [QA_RESULTS_SUMMARY.md](QA_RESULTS_SUMMARY.md) | Tổng hợp QA, bug story |
| [JUDGING_CRITERIA_MAPPING.md](JUDGING_CRITERIA_MAPPING.md) | Map vào 4 tiêu chí chấm điểm |
| [DEMO_INPUTS_AND_EXPECTED_OUTPUTS.md](DEMO_INPUTS_AND_EXPECTED_OUTPUTS.md) | Input/output cụ thể cho từng demo |
| [LIMITATIONS_AND_ROADMAP.md](LIMITATIONS_AND_ROADMAP.md) | Hạn chế trung thực + roadmap |
| [MVP_SCOPE.md](MVP_SCOPE.md) | Phạm vi MVP Beta vs GA |
| [PRESENTATION_TALK_TRACK.md](PRESENTATION_TALK_TRACK.md) | Lời thoại quay video tiếng Việt |
