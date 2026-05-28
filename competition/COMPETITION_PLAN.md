# 🏆 KẾ HOẠCH DỰ THI — MongoDB Recommendation Engine

**Deadline:** 31/05/2026 · 18:00 VNT  
**Còn lại:** ~3 ngày  
**Định vị:** *Universal Recommendation Engine* — demo bằng use case Legal AI

---

## Phân tích điểm mạnh

| Tiêu chí | Trọng số | Đánh giá | Lý do |
|----------|----------|----------|-------|
| Sáng tạo / Nguyên bản | 30% | ★★★★★ | Domain pháp lý = unique, không ai làm |
| Triển khai kỹ thuật | 30% | ★★★★★ | 7-stage pipeline, hybrid fusion, multilingual |
| Ảnh hưởng / Tiềm năng | 30% | ★★★★★ | LegalTech là thị trường $30B, chưa ai làm ở VN |
| Trình bày / Demo | 10% | ★★★★☆ | Cần polish video + docs |

**Dự đoán:** Top 3 nếu demo mượt, Top 1 nếu có data đẹp.

---

## Bộ file cần nộp

```
competition/
├── VIDEO_SCRIPT.md          ← Kịch bản video 10 phút (file này)
├── SLIDES_CONTENT.md        ← Nội dung slide → paste vào NotebookLM
├── TECHNICAL_DOCS.md        ← Tài liệu kỹ thuật bắt buộc
└── COMPETITION_PLAN.md      ← File này
```

---

## Lịch làm việc (28/05 → 31/05)

### Ngày 28/05 (Hôm nay) — Chuẩn bị tài liệu
- [x] Tạo COMPETITION_PLAN.md
- [x] Tạo VIDEO_SCRIPT.md  
- [x] Tạo SLIDES_CONTENT.md
- [x] Tạo TECHNICAL_DOCS.md
- [ ] Review và chỉnh sửa nội dung

### Ngày 29/05 — Chuẩn bị demo
- [ ] Seed data đẹp vào MongoDB (ít nhất 20 documents pháp lý)
- [ ] Test toàn bộ API endpoints sẽ demo
- [ ] Chụp screenshots các màn hình key
- [ ] Tạo slide deck từ SLIDES_CONTENT.md

### Ngày 30/05 — Quay video
- [ ] Set up màn hình demo (app + MongoDB Atlas dashboard)
- [ ] Quay video theo script (10 min)
- [ ] Edit, thêm subtitle/captions
- [ ] Export final video

### Ngày 31/05 — Nộp bài
- [ ] Final review tài liệu kỹ thuật
- [ ] Upload video lên YouTube/Drive
- [ ] Điền form nộp bài trước 17:00 (buffer 1 tiếng)
- [ ] Submit: https://forms.gle/uV87nmr1XX712aAx9

---

## Chiến lược trình bày (Dual Positioning)

### Frame 1 — Mở đầu (Tổng quát)
> "Chúng tôi xây dựng một Recommendation Engine có thể áp dụng cho bất kỳ domain nào — sản phẩm, nội dung, hay dịch vụ chuyên môn. Hôm nay chúng tôi demo trên domain khó nhất: **pháp lý**."

### Frame 2 — Demo (Cụ thể, ấn tượng)
- Show real-time gợi ý điều luật → "Engine này hiểu ngữ nghĩa, không chỉ keyword"
- Show cross-language (hỏi tiếng Anh → tìm được văn bản tiếng Việt)
- Show personalization (user khác nhau → gợi ý khác nhau)

### Frame 3 — Technical Deep Dive (MongoDB)
- `$vectorSearch` với 384-dim embeddings → similarity search
- Aggregation Pipeline → collaborative filtering + behavior scoring
- 6-signal reranking pipeline

### Frame 4 — Impact (Đóng mạnh)
> "Nếu engine này áp dụng cho e-commerce, nó gợi ý sản phẩm.
> Nếu cho streaming, nó gợi ý phim.  
> Nhưng khi áp dụng cho pháp lý — nó có thể thay đổi cách 97 triệu người Việt tiếp cận công lý."

---

## Checklist trước khi nộp

- [ ] Video ≤ 10 phút, âm thanh rõ
- [ ] Tài liệu kỹ thuật đủ 3 phần bắt buộc
- [ ] MongoDB Vector Search được đề cập + demo rõ ràng
- [ ] Aggregation Pipeline được mô tả + code snippet
- [ ] Use case thực tế, có giá trị
- [ ] Link video hoạt động
