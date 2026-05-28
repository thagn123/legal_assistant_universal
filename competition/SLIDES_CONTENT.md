# 📊 NỘI DUNG SLIDE — PASTE VÀO NOTEBOOKLM
## MongoDB Recommendation Engine — LexAI

> **Hướng dẫn:** Copy toàn bộ file này vào NotebookLM để tạo bản slide. Mỗi section "---" là một slide riêng.

---

## SLIDE 1 — TRANG BÌA

**Tiêu đề chính:**  
LexAI — AI-Powered Legal Recommendation Engine

**Tiêu đề phụ:**  
Gợi ý kiến thức pháp lý thông minh · Xây trên MongoDB Atlas

**Tagline:**  
*"Mọi người đều xứng đáng được tư vấn đúng lúc"*

**Logo / Visual:** MongoDB Atlas Logo + Scales of Justice icon

---

## SLIDE 2 — VẤN ĐỀ

**Tiêu đề:** Bài toán pháp lý tại Việt Nam

**Số liệu ấn tượng (3 cột):**
- 97 triệu người dân — phần lớn không có khả năng thuê luật sư
- 500.000–2.000.000đ/giờ — chi phí tư vấn pháp lý trung bình
- Hàng nghìn văn bản luật — khó tra cứu nếu không chuyên môn

**Pain points (3 điểm):**
1. Người dùng không biết mình cần điều luật nào — chỉ mô tả được vấn đề
2. Văn bản pháp lý dài, ngôn ngữ đặc thù, trộn tiếng Anh/Việt
3. Luật thay đổi thường xuyên — khó theo kịp

**Visual:** Người đứng trước mê cung văn bản pháp luật

---

## SLIDE 3 — GIẢI PHÁP

**Tiêu đề:** LexAI — Recommendation Engine cho Pháp lý

**Định nghĩa:**  
*Một engine gợi ý kiến thức pháp lý 7 tầng, hoàn toàn trên MongoDB Atlas — semantic search + collaborative filtering + personalization.*

**3 khả năng cốt lõi:**

🔍 **Semantic Understanding**  
Hiểu nghĩa câu hỏi tự nhiên, không chỉ keyword matching

🤝 **Collaborative Intelligence**  
Học từ hành vi cộng đồng — người có tình huống tương tự cần gì?

👤 **Deep Personalization**  
Gợi ý khác nhau cho từng người dùng, nhớ cross-session

**Visual:** 3 icon tương ứng với 3 khả năng

---

## SLIDE 4 — KIẾN TRÚC HỆ THỐNG

**Tiêu đề:** 7-Stage Intelligence Pipeline

**Diagram (trái sang phải):**

```
[User Query]
    ↓
Stage 1: Query Planner ——→ Domain detection, Entity extraction (<10ms)
    ↓
Stage 2: Session Memory ——→ MongoDB TTL 24h, conversation context
    ↓
Stage 3: Retrieval Fusion ——→ Vector(0.45) + BM25(0.20) + Graph(0.25) + Behavior(0.10)
    ↓
Stage 4: GraphRAG ——→ BFS traversal, AMENDS/OVERRIDES/CITES edges
    ↓
Stage 5: LLM Reasoning ——→ OpenAI tool-calling, deterministic fallback
    ↓
Stage 6: Reranking ——→ 6 signals: semantic·behavior·graph·freshness·popularity·accepted
    ↓
Stage 7: Persist & Learn ——→ Save trace, update user memory, ReflectionAgent
    ↓
[Personalized Response]
```

**Tech Stack (footer):**  
Python · FastAPI · MongoDB Atlas · React 19 · sentence-transformers · OpenAI

---

## SLIDE 5 — MONGODB VECTOR SEARCH

**Tiêu đề:** Semantic Search với MongoDB $vectorSearch

**Code snippet:**
```javascript
db.law_chunks.aggregate([
  {
    $vectorSearch: {
      index: "law_chunks_embedding",
      path: "embedding",        // 384-dim cosine similarity
      queryVector: queryEmbed,  // user query → embedding
      numCandidates: 150,
      limit: 20,
      filter: {
        $or: [
          { user_id: currentUser },
          { is_global: true }    // admin-uploaded public docs
        ]
      }
    }
  },
  { $addFields: { score: { $meta: "vectorSearchScore" } } }
])
```

**Key features (3 cột):**
- **384 dimensions** · Multilingual model · Hiểu Việt + Anh
- **Cosine similarity** · Tìm nghĩa gần nhất, không phải exact match
- **Hybrid filter** · User isolation + global documents

**Kết quả:** "Article 1" → tìm được "Điều 1 — Định nghĩa" trong văn bản tiếng Việt

---

## SLIDE 6 — AGGREGATION PIPELINE / COLLABORATIVE FILTERING

**Tiêu đề:** Collaborative Filtering trên MongoDB Aggregation

**Ý tưởng:**  
*"Người dùng có hành vi tương tự bạn đã đọc gì? → Gợi ý điều đó cho bạn."*

**Pipeline (5 bước):**

```
interactions collection
        ↓
[1] Match: lấy docs user đã view/save
        ↓
[2] Lookup: tìm users khác tương tác cùng docs
        ↓
[3] Group: tính common_interactions score
        ↓
[4] Lookup: lấy docs peers xem mà user chưa thấy
        ↓
[5] Sort + Limit: top-10 collaborative recommendations
```

**Không cần:** ML framework, Python matrix operations, external service  
**Chỉ cần:** MongoDB Aggregation Pipeline — 100% in-database

**4 collections involved:**
- `interactions` — view/save/download events
- `law_chunks` — document embeddings
- `user_memory` — persistent cross-session profiles
- `conversation_sessions` — 24h TTL context

---

## SLIDE 7 — 6-SIGNAL RERANKING

**Tiêu đề:** Personalized Reranking — 6 tín hiệu

**Bảng trọng số:**

| Tín hiệu | Trọng số | Ý nghĩa |
|----------|----------|---------|
| Semantic similarity | 35% | Gần với query của user |
| Behavior score | 15% | User đã tương tác loại này trước |
| Graph relevance | 20% | Liên kết pháp lý trong đồ thị |
| Freshness | 15% | Luật mới hơn được ưu tiên |
| Popularity | 10% | Nhiều người dùng tương tác |
| Accepted rate | 5% | Tỷ lệ feedback tích cực |

**Công thức freshness:**  
`score = exp(-ln(2)/180 × days)` → half-life 180 ngày

**Kết quả:** Cùng một câu hỏi, 2 users khác nhau → 2 bộ kết quả khác nhau

---

## SLIDE 8 — MULTILINGUAL RETRIEVAL

**Tiêu đề:** Cross-Language — Hỏi Anh, Tìm Việt

**Vấn đề:**  
Văn bản pháp lý Việt Nam trộn lẫn tiếng Anh (contract law, arbitration, force majeure)

**Giải pháp — 3 tầng:**

1. **Language Detection** · Phát hiện VI/EN với điểm tin cậy, jurisdiction (VN/US/EU)
2. **Canonical References** · "Điều 1" = "Article 1" = `article_1` (stable ID)  
3. **ALIAS_OF Edges** · Graph links giữa node cùng nghĩa khác ngôn ngữ

**Kết quả đo lường:**
- Cross-language hit rate: **100%** trên test set
- ALIAS_OF edges tự động: **20 edges/document**
- Canonical refs: **28–31 refs/document**

---

## SLIDE 9 — DEMO SCREENSHOTS

**Tiêu đề:** Demo — Gợi ý Thông Minh Hoạt Động Thực Tế

**[4 screenshot layout:]**

**Top-left:** Chat interface — câu hỏi tự nhiên về tranh chấp lao động  
**Top-right:** Dashboard — personalized feed + behavior chart  
**Bottom-left:** MongoDB Atlas — law_chunks với embeddings  
**Bottom-right:** Aggregation result — collaborative recommendations

**Caption:** "Từ câu hỏi tự nhiên → văn bản pháp lý chính xác — trong dưới 2 giây"

---

## SLIDE 10 — DATA ARCHITECTURE

**Tiêu đề:** Data Schema — MongoDB Atlas

**Collections (6 boxes):**

```
law_chunks {
  text, embedding[384], user_id,
  is_global, canonical_refs[],
  language, hierarchy_path
}

interactions {
  user_id, doc_id, event_type,
  timestamp, session_id
}

user_memory {
  user_id, personal_info{name,age,...},
  situation_summaries[20], updated_at
  // NO TTL — permanent memory
}

conversation_sessions {
  session_id, history[], last_active
  // TTL: 24h auto-cleanup
}

reasoning_traces {
  trace_id, stages[], retrieval_context,
  timing, signals_fired[]
}

law_cases {
  case_id, facts, holdings,
  embedding[384], citations[]
}
```

**Vector Index:** `law_chunks.embedding` · 384-dim · cosine · `$vectorSearch`

---

## SLIDE 11 — IMPACT & MARKET

**Tiêu đề:** Impact — Tại Sao Điều Này Quan Trọng

**Market size:**
- 🇻🇳 97 triệu dân, LegalTech VN còn sơ khai
- 🌏 LegalTech toàn cầu: $30B+ (2026), CAGR 10%+
- 💼 SMEs VN: 800.000+ doanh nghiệp cần tư vấn pháp lý thường xuyên

**So sánh:**

| | Tư vấn truyền thống | LexAI |
|--|---------------------|-------|
| Thời gian | 2–5 ngày | < 2 giây |
| Chi phí | 500K–2M đ/giờ | Gần 0 |
| Availability | Giờ hành chính | 24/7 |
| Ngôn ngữ | Tiếng Việt | Việt + Anh |
| Cập nhật luật | Manual | Tự động |

**Quote:**  
*"Nếu Google Maps dân chủ hóa việc tìm đường, LexAI dân chủ hóa việc tìm công lý."*

---

## SLIDE 12 — SCALABILITY

**Tiêu đề:** Kiến Trúc Mở Rộng Được — Cho Mọi Domain

**Đây không chỉ là Legal AI. Đây là universal recommendation infrastructure.**

**Thay đổi domain trong < 1 giờ:**

| law_chunks → | = | Recommendation cho |
|---|---|---|
| product_catalog | → | E-commerce (Shopee, Tiki) |
| movie_metadata | → | Streaming (Netflix, FPT Play) |
| medical_guidelines | → | HealthTech |
| course_content | → | EdTech (Coursera VN) |
| news_articles | → | Media personalization |

**Không thay đổi:**  
✅ MongoDB $vectorSearch ✅ Aggregation Pipeline ✅ 6-signal reranking ✅ Collaborative filter

---

## SLIDE 13 — TECHNICAL HIGHLIGHTS

**Tiêu đề:** Điểm Kỹ Thuật Nổi Bật

**6 điểm độc đáo:**

1. **Hybrid Retrieval Fusion** — 4 tín hiệu normalized + weighted sum, không phải chọn 1
2. **GraphRAG** — BFS trên đồ thị pháp lý (AMENDS, OVERRIDES, CONFLICTS_WITH edges)
3. **ReflectionAgent** — daemon thread học từ conversation, không block response
4. **Cross-language Canonical IDs** — "Điều 1" = "Article 1" = `article_1`
5. **Admin Global Documents** — is_global=True, visible cho tất cả users không cần copy
6. **Deterministic Fallback** — không có OpenAI? Pipeline vẫn chạy hoàn toàn

---

## SLIDE 14 — ROADMAP

**Tiêu đề:** Roadmap Phát Triển

**Q3 2026:**
- BGE-M3 embedding (tốt hơn cho tiếng Việt)
- Real-time feedback loop vào reranking
- Mobile app (React Native)

**Q4 2026:**
- API public cho luật sư, công ty luật
- Document comparison (tìm xung đột giữa các điều luật)
- Integration với Cổng thông tin pháp luật VN

**2027:**
- Mở rộng: luật ASEAN (Thái, Indonesia, Malaysia)
- B2B SaaS cho doanh nghiệp

---

## SLIDE 15 — KẾT LUẬN

**Tiêu đề:** LexAI — Recommendation Engine Cho Pháp Lý Việt Nam

**3 điều cần nhớ:**

> 🧠 **Thông minh** — Semantic search + collaborative filtering + personalization  
> 🏗️ **Vững chắc** — MongoDB Atlas, 7-stage pipeline, deterministic fallback  
> 🌍 **Có giá trị** — 97 triệu người, thị trường chưa ai khai thác

**Built with:**  
MongoDB Atlas · $vectorSearch · Aggregation Pipeline · Python · FastAPI · React

**Team:** [Tên nhóm]  
**Contact:** [Email]  
**Demo:** localhost:3000 · API: localhost:8001

*"Mọi người đều xứng đáng được tư vấn đúng lúc."*
