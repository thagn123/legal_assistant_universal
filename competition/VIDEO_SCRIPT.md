# 🎬 KỊCH BẢN VIDEO — 10 PHÚT
## MongoDB Recommendation Engine Competition

---

## TỔNG QUAN

| Phần | Thời gian | Nội dung |
|------|-----------|---------|
| Hook | 0:00–0:40 | Vấn đề, câu hỏi gây tò mò |
| Giới thiệu | 0:40–2:00 | Use case + giải pháp |
| Architecture | 2:00–3:30 | Kiến trúc hệ thống |
| Demo Live | 3:30–7:00 | Demo app thực tế |
| MongoDB Deep Dive | 7:00–9:00 | Vector Search + Aggregation |
| Closing | 9:00–10:00 | Impact + Roadmap |

---

## PHẦN 1 — HOOK (0:00–0:40)

**[Màn hình đen, chữ trắng xuất hiện từng dòng]**

> *"Mỗi năm, hàng triệu người Việt gặp vấn đề pháp lý..."*  
> *"...nhưng không biết bắt đầu từ đâu."*  
> *"Không phải vì luật không tồn tại."*  
> *"Mà vì không ai gợi ý đúng điều luật họ cần."*

**[Cắt sang màn hình app]**

**Giọng thuyết minh:**
> "Hôm nay chúng tôi giới thiệu một Recommendation Engine — không gợi ý phim hay sản phẩm — mà gợi ý **kiến thức pháp lý**, đúng lúc, đúng người, đúng nhu cầu."

---

## PHẦN 2 — GIỚI THIỆU (0:40–2:00)

**[Slide: Vấn đề]**

**Giọng thuyết minh:**
> "Bài toán recommendation trong domain pháp lý khó hơn gợi ý phim rất nhiều:
> - Văn bản pháp lý dài hàng trăm trang, ngôn ngữ đặc thù
> - Người dùng không biết mình cần điều luật nào — họ chỉ mô tả vấn đề
> - Tiếng Việt và tiếng Anh trộn lẫn
> - Sai một điều khoản có thể gây hậu quả nghiêm trọng"

**[Slide: Giải pháp]**

> "Chúng tôi xây dựng **LexAI** — Universal Legal Knowledge Assistant — một Recommendation Engine 7 tầng, hoàn toàn trên MongoDB Atlas."

**[Hiển thị 3 tính năng core]**
> "Ba điểm cốt lõi:
> 1. **Semantic Search** — hiểu nghĩa, không chỉ keyword
> 2. **Collaborative Filtering** — học từ hành vi cộng đồng pháp lý
> 3. **Personalization** — gợi ý khác nhau cho từng người dùng"

---

## PHẦN 3 — ARCHITECTURE (2:00–3:30)

**[Slide: Sơ đồ kiến trúc]**

**Giọng thuyết minh:**
> "Kiến trúc gồm 7 tầng xử lý:"

**[Highlight từng stage khi đọc]**

> "Stage 1 — **Query Planner**: phân tích truy vấn, phát hiện domain pháp lý, trích xuất thực thể. Không dùng AI — hoàn toàn deterministic, dưới 10ms.

> Stage 2 — **Session Memory**: lịch sử 24 giờ từ MongoDB với TTL index tự động.

> Stage 3 — **Retrieval Fusion**: đây là trái tim của engine. Kết hợp 4 tín hiệu:
> - MongoDB **$vectorSearch** — 384 chiều cosine similarity, trọng số 0.45
> - BM25 keyword scoring — trọng số 0.20
> - Graph traversal — trọng số 0.25
> - Behavior boost — trọng số 0.10

> Stage 4 — **GraphRAG**: duyệt đồ thị pháp lý, tìm điều luật liên quan, điều sửa đổi, điều xung đột.

> Stage 5 — **LLM Reasoning**: OpenAI tool-calling, tổng hợp chứng cứ, fallback deterministic khi offline.

> Stage 6 — **Reranking**: 6 tín hiệu cá nhân hóa — semantic, behavior, graph, freshness, popularity, acceptance.

> Stage 7 — **Persist & Learn**: lưu trace, cập nhật memory người dùng, trigger reflection agent."

---

## PHẦN 4 — DEMO LIVE (3:30–7:00)

### Scene 4.1 — Truy vấn tự nhiên (3:30–4:30)

**[Mở browser, vào app localhost:3000]**

**Giọng thuyết minh:**
> "Tôi đóng vai một người vừa bị sa thải. Tôi không biết mình cần tìm điều luật nào."

**[Gõ vào ô chat:]**  
`"Công ty tôi tự dưng cho tôi nghỉ việc không có lý do, tôi phải làm gì?"`

**[Chờ kết quả, highlight từng phần]**
> "Trong vài giây, engine đã:
> - Phân loại domain: **lao động** (lao_dong)
> - Gợi ý Điều 36 Bộ luật Lao động — quyền đơn phương chấm dứt hợp đồng
> - Gợi ý biểu mẫu khiếu nại phù hợp
> - Cảnh báo rủi ro pháp lý liên quan BHXH"

### Scene 4.2 — Cross-language (4:30–5:15)

**[Tab mới, gõ tiếng Anh:]**  
`"Article 36 labor code Vietnam termination rights"`

**[Highlight kết quả]**
> "Tôi hỏi bằng tiếng Anh — engine tìm được **Điều 36 Bộ luật Lao động** bằng tiếng Việt. Cross-language retrieval — không cần translation API, hoàn toàn từ embedding space."

### Scene 4.3 — Personalization (5:15–6:00)

**[Chuyển sang tab Dashboard]**
> "Sau vài lần tương tác, Dashboard tự cập nhật:
> - 'AI nhớ bạn quan tâm đến tranh chấp lao động'
> - Gợi ý chủ động: checklist quyền người lao động
> - So sánh hành vi với người dùng cùng tình huống (collaborative filtering)"

**[Mở MongoDB Atlas, show collection `interactions`]**
> "Mỗi tương tác được log vào MongoDB — view, save, download — để feed vào collaborative filter."

### Scene 4.4 — Admin Upload (6:00–7:00)

**[Chuyển sang /admin/login]**
> "Luật mới ban hành? Admin upload file .doc/.pdf — pipeline 8 stage tự động:
> extract → structure → chunk → embed → index vào MongoDB.
> Trong vài phút, toàn bộ người dùng có thể tìm kiếm văn bản mới."

**[Show MongoDB Atlas, collection `law_chunks` tăng thêm documents]**

---

## PHẦN 5 — MONGODB DEEP DIVE (7:00–9:00)

### Scene 5.1 — Vector Search (7:00–7:50)

**[Chuyển sang MongoDB Atlas → Collections → law_chunks]**

**Giọng thuyết minh:**
> "Đây là collection `law_chunks` — mỗi document có field `embedding` là vector 384 chiều."

**[Show một document, highlight field `embedding`]**

> "Chúng tôi dùng sentence-transformers để tạo embedding từ text pháp lý tiếng Việt. Model multilingual — hiểu cả Việt lẫn Anh trong cùng không gian vector."

**[Chuyển sang Aggregation tab, show query:]**
```javascript
{
  $vectorSearch: {
    index: "law_chunks_embedding",
    path: "embedding",
    queryVector: [...],  // embedding của câu hỏi người dùng
    numCandidates: 150,
    limit: 20,
    filter: {
      $or: [
        { user_id: "user_abc123" },
        { is_global: true }
      ]
    }
  }
}
```

> "Filter đảm bảo mỗi user chỉ thấy document của họ + document admin upload toàn hệ thống."

### Scene 5.2 — Aggregation Pipeline / Collaborative Filtering (7:50–9:00)

**[Show Aggregation Pipeline trong Atlas]**

> "Collaborative filtering chạy hoàn toàn bằng MongoDB Aggregation. Không cần ML framework ngoài."

**[Show pipeline từng stage]**
```javascript
// Stage 1: Lấy interaction của user hiện tại
{ $match: { user_id: "user_abc123", event_type: { $in: ["view", "save"] } } }

// Stage 2: Lookup users có interaction tương tự
{ $lookup: { from: "interactions", ... } }

// Stage 3: Tính similarity score giữa các users
{ $group: { _id: "$peer_user", common_docs: { $sum: 1 } } }

// Stage 4: Lấy documents peers đã tương tác mà user chưa thấy
{ $lookup: { from: "law_chunks", ... } }

// Stage 5: Score và sort
{ $sort: { peer_score: -1 } }
{ $limit: 10 }
```

> "Kết quả: documents được gợi ý từ cộng đồng người dùng có hành vi tương tự — collaborative filtering thuần MongoDB."

---

## PHẦN 6 — IMPACT & CLOSING (9:00–10:00)

**[Slide: Con số]**

**Giọng thuyết minh:**
> "Với engine này:
> - **Thị trường**: 97 triệu người Việt — đa số không có điều kiện thuê luật sư
> - **Tốc độ**: truy vấn pháp lý trong dưới 2 giây thay vì vài ngày tư vấn
> - **Chi phí**: gần như 0 so với phí tư vấn pháp lý trung bình 500.000–2.000.000đ/giờ"

**[Slide: Kiến trúc có thể mở rộng]**

> "Nhưng quan trọng hơn — kiến trúc này **không bị giới hạn bởi domain pháp lý**.
> 
> Cùng engine này, thay `law_chunks` bằng `product_catalog` → bạn có e-commerce recommender.  
> Thay bằng `movie_metadata` → streaming recommender.  
> Thay bằng `medical_guidelines` → clinical decision support.
>
> MongoDB Vector Search + Aggregation Pipeline = infrastructure của bất kỳ Recommendation Engine nào."

**[Slide: Roadmap]**

> "Roadmap tiếp theo:
> - Tích hợp BGE-M3 embedding — tốt hơn cho tiếng Việt
> - Real-time reranking với feedback loop
> - Mobile app — tiếp cận người dùng không có laptop"

**[Slide cuối: Logo + Link]**

> "LexAI — Recommendation Engine cho pháp lý Việt Nam.  
> Xây trên MongoDB Atlas.  
> Vì mọi người đều xứng đáng được tư vấn đúng lúc."

**[Fade out]**

---

## GHI CHÚ QUAY VIDEO

### Setup màn hình
- Browser: localhost:3000 (React app)
- MongoDB Atlas tab: mở sẵn Collections + Aggregation
- Terminal: hiển thị logs khi demo (optional)
- Resolution: 1920x1080, font size lớn hơn bình thường

### Tips
- Dùng chuột highlight rõ ràng trước khi đọc
- Pause nhẹ sau mỗi kết quả để người xem đọc
- Nếu có lỗi live → có sẵn screenshots backup
- Record audio riêng, edit sau nếu cần

### Backup plan
- Nếu MongoDB chậm: dùng recorded session replay
- Nếu API lỗi: show Postman với kết quả đã chuẩn bị
