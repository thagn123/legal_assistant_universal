# Limitations & Roadmap — LexAI / ULKA

Chúng tôi không che giấu hạn chế. Hệ thống có release gate tự động phát hiện và báo cáo.

---

## Current Limitations

### L-01 — case_embedding_index không tạo được (Infrastructure)

**Mô tả:** MongoDB Atlas M0 free tier giới hạn tối đa 3 vector search indexes. Đã dùng hết:
- `chunk_embedding_index` → chunks_vec ✅ (active, primary retrieval)
- `template_embedding_index` → templates ✅ (active)
- `risk_embedding_index` → risks ✅ (active)

`case_embedding_index` trên `legal_cases` không thể tạo thêm.

**Hệ quả:**
- Similar cases dùng demo fallback (`is_demo=True`)
- `fallback_demo_rate = 100%`
- GA gate FAIL

**Không phải lỗi code.** Domain classifier, law retrieval, OutputValidator, evidence extraction đều hoạt động bình thường.

**Transparency:** Release gate tự động phát hiện và báo cáo:
```
❌ fallback_demo_rate_pct: 100.0 > 30.0 (target)
```

**Giải pháp:** Upgrade Atlas M0 → M10+ (~$57/month) → tạo `case_embedding_index` → GA gate PASS.

---

### L-02 — Fallback/demo rate = 100%

**Hệ quả trực tiếp của L-01.** Tất cả `/recommendations/cases` và similar case retrieval trả về demo data.

**Frontend transparency:** Demo cases hiển thị badge "Ví dụ tham khảo" — không bao giờ giả là kết quả thật.

---

### L-03 — avg_top1_score = 0.52 (thấp hơn target 0.55)

**Root cause:** Demo fallback luôn trả score cố định 0.50. Benchmark ghi nhận tất cả queries là `is_fallback=True` vì Atlas M0 không có `case_embedding_index` — dẫn đến avg bị kéo xuống 0.52.

**Không phải model kém.** Law chunk retrieval (chunks_vec) có scores thực tế, và Q17/Q29 có scores 0.87 khi vector search thật hoạt động.

---

### L-04 — Q28 Non-legal query domain = hop_dong

**Mô tả:** Query "Hôm nay thời tiết đẹp, đi đâu ăn?" trả về domain `hop_dong` thay vì `general`.

**Root cause:** Không có zero-score guard — khi không có legal keyword nào khớp, classifier fall về domain đầu tiên có bất kỳ match nhỏ nào.

**Impact:** Minor UX. Manual QA S-15 test với query khác và pass vì content không hallucinate pháp lý.

---

### L-05 — Q03 Cross-domain ambiguity

**Mô tả:** "GCN QSDĐ bị UBND thu hồi không bồi thường, khiếu nại ở đâu?" → `hanh_chinh` thay vì `dat_dai` trong benchmark.

**Đây không phải bug.** Query này vừa liên quan đến đất đai (thu hồi đất) vừa liên quan đến hành chính (khiếu nại quyết định). Manual QA S-03 tester đánh giá response quality — cả hai topic được đề cập → PASS.

---

### L-06 — Load testing chưa thực hiện

**Mô tả:** Chưa test ≥10 concurrent users. Production readiness requirement.

---

### L-07 — Lawyer-in-the-loop chưa có

**Mô tả:** AI không thể đảm bảo tư vấn pháp lý cuối cùng. Cần human expert review.

---

## Roadmap

### Short-term (1–2 tháng)

| Task | Priority | Impact |
|---|---|---|
| Upgrade Atlas M0 → M10+ | P0 | GA gate PASS |
| Tạo `case_embedding_index` trên `legal_cases` | P0 | Real similar cases |
| Seed thêm legal cases từ thực tế | P1 | Chất lượng similar cases |
| Non-legal query guard (zero-score → general) | P1 | Fix L-04 |
| Load test ≥10 concurrent users | P2 | Production readiness |

### Mid-term (3–6 tháng)

| Task | Description |
|---|---|
| Contract upload + clause analysis | User upload hợp đồng → phân tích risk |
| Legal document viewer | Citation highlighting, article navigation |
| Retrieval analytics dashboard | Monitor precision/recall over time |
| Evaluation dataset 50+ scenarios | Expand manual QA beyond 15 |
| Cross-encoder reranker | Improve retrieval quality post-fusion |
| Multi-domain query handling | "Sa thải + đất đai" → split pipeline |

### Long-term (6–12 tháng)

| Task | Description |
|---|---|
| Lawyer-in-the-loop | AI draft → luật sư review và ký xác nhận |
| Enterprise integration | Legal workflow cho doanh nghiệp vừa và nhỏ |
| Gov API integration | Kết nối cổng thông tin pháp luật Việt Nam |
| Multilingual | English legal assistant |
| Mobile app | Native iOS/Android |
| Production monitoring | Alerting khi accuracy drop, error spike |

---

## Tại sao Limitations là điểm mạnh

Trong hackathon, nhiều dự án hide limitations hoặc không có cơ chế detect.

**LexAI chọn hướng ngược lại:**

1. **Release gate tự động** — phát hiện và báo cáo bất kỳ blocker nào trước khi deploy
2. **Demo fallback label** — `is_demo=True` trong response, badge trong UI — người dùng biết
3. **QA documentation** — `qa/beta_ga_status.md` ghi rõ từng bug, root cause, fix path
4. **Benchmark transparency** — mọi query result được ghi rõ `is_fallback`, `is_demo` fields

**Đây là engineering culture đúng đắn cho AI trong lĩnh vực pháp lý.**  
Một legal AI sai lầm có thể gây thiệt hại thật sự cho người dùng. Transparency không phải điểm yếu — là điều kiện cần.
