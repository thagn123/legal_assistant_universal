# 📋 TÀI LIỆU KỸ THUẬT
## LexAI — AI-Powered Legal Recommendation Engine
### MongoDB Recommendation Engine Competition 2026

---

## PHẦN 1 — MVP & KIẾN TRÚC HỆ THỐNG

### 1.1 MVP Definition

**LexAI** là một Recommendation Engine chuyên domain pháp lý, cung cấp:

- **Semantic document retrieval** — tìm kiếm văn bản pháp lý theo nghĩa, không chỉ từ khóa
- **Collaborative filtering** — gợi ý dựa trên hành vi cộng đồng người dùng tương tự
- **Personalized reranking** — 6 tín hiệu cá nhân hóa kết quả cho từng user
- **Cross-language search** — hỏi tiếng Anh, tìm được văn bản tiếng Việt và ngược lại
- **Continuous learning** — engine học từ mỗi tương tác, không cần retrain

### 1.2 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Python 3.11 · FastAPI · Uvicorn |
| Database | MongoDB Atlas (M0 Free → M10 Production) |
| Embeddings | sentence-transformers (paraphrase-multilingual-mpnet-base-v2) |
| LLM | OpenAI GPT-4o (optional, deterministic fallback) |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS |
| Auth | Header-based (X-User-ID, X-Admin-Key) |
| Storage | MongoDB Atlas + SQLite (job queue) |

### 1.3 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│  React 19 Frontend (localhost:3000)                         │
│  Pages: Dashboard · Analyze · Contract · Risks · Documents  │
└─────────────────────┬───────────────────────────────────────┘
                       │ HTTP/REST
┌─────────────────────▼───────────────────────────────────────┐
│                         API LAYER                            │
│  FastAPI (localhost:8001)                                    │
│  ├── /intelligence/analyze  ← 7-stage pipeline              │
│  ├── /recommendations/*     ← 6 recommender types           │
│  ├── /admin/*               ← Global document management    │
│  └── /interactions/log      ← Behavior tracking             │
└─────────────────────┬───────────────────────────────────────┘
                       │
┌─────────────────────▼───────────────────────────────────────┐
│                    INTELLIGENCE ENGINE                        │
│                                                              │
│  Stage 1: QueryPlanner (deterministic, <10ms)               │
│  Stage 2: SessionStore (MongoDB TTL 24h)                     │
│  Stage 3: RetrievalFusionEngine                             │
│    ├── $vectorSearch (weight: 0.45)                         │
│    ├── BM25 TF-IDF approximation (weight: 0.20)             │
│    ├── GraphRAG traversal (weight: 0.25)                    │
│    └── Behavior boost (weight: 0.10)                        │
│  Stage 4: GraphRAG BFS (AMENDS/OVERRIDES/CITES edges)       │
│  Stage 5: LLM Reasoning (OpenAI tool-calling, max 4 rounds) │
│  Stage 6: RecommendationRanker (6 signals)                  │
│  Stage 7: Persist + ReflectionAgent (daemon thread)         │
└─────────────────────┬───────────────────────────────────────┘
                       │
┌─────────────────────▼───────────────────────────────────────┐
│                    DATA LAYER                                │
│  MongoDB Atlas                                               │
│  ├── law_chunks (384-dim Vector Index)                      │
│  ├── interactions (behavior tracking)                       │
│  ├── user_memory (permanent personalization)                │
│  ├── conversation_sessions (24h TTL)                        │
│  └── reasoning_traces (observability)                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Document Ingestion Pipeline (8 stages)

Khi admin upload văn bản pháp lý mới:

```
Upload (.doc/.pdf/.html)
    ↓
Stage 1: Profiler — phát hiện loại file, layout complexity
    ↓
Stage 2: Extractor — extract text blocks, tables, images
    ↓
Stage 3: Cleaner — OCR cleanup, normalize encoding
    ↓
Stage 4: Structurer — phát hiện Chương/Điều/Khoản, canonical IDs
    ↓
Stage 5: Chunker — semantic chunking với overlap
    ↓
Stage 6: Graph Builder — tạo nodes/edges, ALIAS_OF cross-language
    ↓
Stage 7: Embedder — sentence-transformers → 384-dim vectors
    ↓
Stage 8: Indexer — upsert vào MongoDB law_chunks
```

---

## PHẦN 2 — DATA SCHEMA & KIẾN TRÚC DỮ LIỆU MONGODB

### 2.1 Collection: `law_chunks`

**Mục đích:** Lưu các đoạn văn bản pháp lý đã được embed, là core của Vector Search.

```javascript
{
  "_id": ObjectId("..."),
  "chunk_id": "chunk_doc123_p1_b0_c0",
  "document_id": "doc_edd4c13282a800eb",
  "user_id": "admin",          // "admin" = global, user_id = private
  "is_global": true,           // true → visible to ALL users
  
  // Content
  "text": "Điều 1. Phạm vi điều chỉnh\nLuật này quy định về...",
  "chunk_type": "text",        // text | table | image
  "source_filename": "45_2019_QH14.doc",
  
  // Multilingual metadata
  "language": "vi",            // vi | en | mixed
  "canonical_refs": ["article_1", "chapter_1"],  // language-agnostic IDs
  "hierarchy_path": "chapter_1/article_1",
  
  // Vector
  "embedding": [0.0234, -0.0891, ...],  // 384 dimensions, float32
  
  // Quality
  "token_estimate": 156,
  "confidence": 0.95,
  "degraded": false,
  
  // Timestamps
  "created_at": "2026-05-14T10:30:00Z",
  "processing_version": "1.0.0"
}
```

**Vector Index (Atlas Search Index):**
```json
{
  "name": "law_chunks_embedding",
  "type": "vectorSearch",
  "fields": [{
    "type": "vector",
    "path": "embedding",
    "numDimensions": 384,
    "similarity": "cosine"
  }]
}
```

### 2.2 Collection: `interactions`

**Mục đích:** Tracking hành vi người dùng — input cho collaborative filtering.

```javascript
{
  "_id": ObjectId("..."),
  "user_id": "user_abc123",
  "doc_id": "doc_edd4c13282a800eb",
  "chunk_id": "chunk_doc123_p1_b0_c0",
  "event_type": "save",        // view | save | download | expand
  "session_id": "sess_xyz",
  "query": "tranh chấp lao động",
  "domain": "lao_dong",
  "timestamp": ISODate("2026-05-14T10:30:00Z"),
  "decay_weight": 0.95         // exp(-0.08 * days), half-life ~8.7 days
}
```

### 2.3 Collection: `user_memory`

**Mục đích:** Bộ nhớ vĩnh viễn cross-session — không có TTL.

```javascript
{
  "_id": ObjectId("..."),
  "user_id": "user_abc123",
  "personal_info": {
    "name": "Nguyễn Văn A",
    "age": 32,
    "occupation": "Giám đốc SME",
    "location": "Hà Nội",
    "notes": "Quan tâm hợp đồng lao động và tranh chấp đất đai"
  },
  "situation_summaries": [
    {
      "session_id": "sess_xyz",
      "date": "2026-05-14",
      "domain": "lao_dong",
      "summary": "Người dùng hỏi về quyền lợi khi bị sa thải không có lý do",
      "resolved": false
    }
    // ... last 20 records
  ],
  "updated_at": ISODate("2026-05-14T10:30:00Z")
  // NO TTL INDEX — permanent storage
}
```

### 2.4 Collection: `conversation_sessions`

**Mục đích:** Lịch sử hội thoại 24 giờ. TTL Index tự động cleanup.

```javascript
{
  "_id": ObjectId("..."),
  "session_id": "sess_xyz",
  "user_id": "user_abc123",
  "history": [
    { "role": "user", "content": "Tôi bị sa thải..." },
    { "role": "assistant", "content": "Theo Điều 36 Bộ luật Lao động..." }
  ],
  "law_type_preferences": ["lao_dong", "dan_su"],
  "last_active": ISODate("2026-05-14T10:30:00Z")
  // TTL INDEX on last_active: expireAfterSeconds: 86400
}
```

---

## PHẦN 3 — ÁP DỤNG VECTOR SEARCH & AGGREGATION PIPELINE

### 3.1 MongoDB $vectorSearch — Semantic Retrieval

#### 3.1.1 Embedding Generation

```python
# src/engine/retrieval_fusion.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
# Output: 384-dim float32 vector
# Supports: Vietnamese, English, and 50+ languages in same vector space

def embed_query(query: str) -> list[float]:
    return model.encode(query, normalize_embeddings=True).tolist()
```

#### 3.1.2 Vector Search Query

```python
# Signal 1: Vector Search (weight 0.45)
pipeline = [
    {
        "$vectorSearch": {
            "index": "law_chunks_embedding",
            "path": "embedding",
            "queryVector": embed_query(user_query),
            "numCandidates": 150,   # over-fetch for reranking
            "limit": 20,
            "filter": {
                "$or": [
                    {"user_id": current_user_id},
                    {"is_global": True}
                ]
            }
        }
    },
    {
        "$addFields": {
            "vector_score": {"$meta": "vectorSearchScore"}
        }
    }
]
results = db.law_chunks.aggregate(pipeline)
```

#### 3.1.3 Hybrid Score Fusion

```python
# Min-max normalize each signal, then weighted sum
def fuse_scores(vector_score, bm25_score, graph_score, behavior_score):
    weights = {
        "vector":   0.45,
        "bm25":     0.20,
        "graph":    0.25,
        "behavior": 0.10,
    }
    # Normalize to [0, 1]
    scores = {
        "vector":   normalize(vector_score),
        "bm25":     normalize(bm25_score),
        "graph":    normalize(graph_score),
        "behavior": normalize(behavior_score),
    }
    return sum(weights[k] * scores[k] for k in weights)
```

### 3.2 Aggregation Pipeline — Collaborative Filtering

#### 3.2.1 Behavior-Based Peer Finding

```javascript
// Tìm users có interaction tương tự → gợi ý từ peers
db.interactions.aggregate([
  // Stage 1: Docs user hiện tại đã tương tác
  {
    $match: {
      user_id: "user_abc123",
      event_type: { $in: ["save", "download"] },
      timestamp: { $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) }
    }
  },
  
  // Stage 2: Tìm users khác tương tác cùng docs
  {
    $lookup: {
      from: "interactions",
      localField: "doc_id",
      foreignField: "doc_id",
      as: "peer_interactions",
      pipeline: [
        { $match: { user_id: { $ne: "user_abc123" } } }
      ]
    }
  },
  
  // Stage 3: Tính peer similarity score
  { $unwind: "$peer_interactions" },
  {
    $group: {
      _id: "$peer_interactions.user_id",
      common_docs: { $sum: 1 },
      peer_domain_match: { $first: "$peer_interactions.domain" }
    }
  },
  { $sort: { common_docs: -1 } },
  { $limit: 20 },  // top-20 similar peers
  
  // Stage 4: Lấy docs peers xem mà user chưa thấy
  {
    $lookup: {
      from: "interactions",
      localField: "_id",
      foreignField: "user_id",
      as: "peer_docs"
    }
  },
  { $unwind: "$peer_docs" },
  
  // Stage 5: Lọc docs user chưa xem
  {
    $lookup: {
      from: "interactions",
      let: { docId: "$peer_docs.doc_id" },
      pipeline: [
        {
          $match: {
            $expr: {
              $and: [
                { $eq: ["$user_id", "user_abc123"] },
                { $eq: ["$doc_id", "$$docId"] }
              ]
            }
          }
        }
      ],
      as: "already_seen"
    }
  },
  { $match: { already_seen: { $size: 0 } } },
  
  // Stage 6: Aggregate collaborative score
  {
    $group: {
      _id: "$peer_docs.doc_id",
      collaborative_score: { $sum: "$common_docs" },
      peer_count: { $sum: 1 }
    }
  },
  { $sort: { collaborative_score: -1 } },
  { $limit: 10 }
])
```

#### 3.2.2 Behavior Profile Aggregation

```javascript
// Tính behavior profile của user — dùng trong reranking
db.interactions.aggregate([
  { $match: { user_id: "user_abc123" } },
  
  // Tính domain preferences
  {
    $group: {
      _id: "$domain",
      interaction_count: { $sum: 1 },
      // Decay: tương tác gần đây có trọng số cao hơn
      weighted_score: {
        $sum: {
          $multiply: [
            1,
            { $exp: { $multiply: [-0.08, { $divide: [
              { $subtract: [new Date(), "$timestamp"] },
              86400000  // ms → days
            ]}]}}
          ]
        }
      }
    }
  },
  { $sort: { weighted_score: -1 } }
])
```

### 3.3 6-Signal Reranking

```python
# src/engine/recommendation_ranker.py
class RecommendationRanker:
    WEIGHTS = {
        "semantic":   0.35,
        "behavior":   0.15,
        "graph":      0.20,
        "freshness":  0.15,
        "popularity": 0.10,
        "accepted":   0.05,
    }
    # Constraint: sum(weights) == 1.0

    def _freshness_score(self, created_at: datetime) -> float:
        days = (datetime.now() - created_at).days
        return math.exp(-math.log(2) / 180 * days)  # half-life 180 days

    def rank(self, candidates, user_profile, query_context):
        for doc in candidates:
            doc.final_score = sum(
                self.WEIGHTS[signal] * doc.scores[signal]
                for signal in self.WEIGHTS
            )
        return sorted(candidates, key=lambda d: d.final_score, reverse=True)
```

### 3.4 Cross-Language Canonical References

```python
# src/retrieval/canonical_references.py
# "Điều 1" → "article_1" → tìm được cả node tiếng Anh

TERM_ALIASES = {
    "article": frozenset(["article", "art.", "điều"]),
    "clause":  frozenset(["clause", "khoản"]),
    "section": frozenset(["section", "mục"]),
    "chapter": frozenset(["chapter", "chương"]),
}

def normalize_query(query: str) -> str:
    # "Điều 3" → "article_3"
    # "Article III" → "article_3" (Roman numerals supported)
    # "Art. 3(a)" → "article_3_a"
    ...
```

---

## PHỤ LỤC — API ENDPOINTS

### Core Intelligence
```
POST /intelligence/analyze
Body: { query, user_id, session_id }
Response: { answer, recommendations[], reasoning_trace, session_id }
```

### Recommendations
```
POST /recommendations/situation    → Law chunk recommendations
POST /recommendations/documents    → Hybrid doc recommendations
POST /recommendations/templates    → Contract templates
POST /recommendations/risks        → Legal risk alerts
GET  /recommendations/behavior/proactive → Proactive recommendations
GET  /recommendations/behavior/digest    → Daily digest
```

### Behavior / Memory
```
POST /interactions/log             → Log user interaction
GET  /recommendations/behavior/profile → User behavior profile
GET  /recommendations/behavior/memory  → Cross-session user memory
PUT  /recommendations/behavior/memory  → Update personal info
```

### Admin
```
POST /admin/documents/upload       → Upload global documents
GET  /admin/stats                  → System statistics
```

---

## PHỤ LỤC — HƯỚNG DẪN CHẠY

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Cấu hình .env
MONGO_URI=mongodb+srv://...
MONGO_DB=legal_knowledge_assistant
OPENAI_API_KEY=sk-...  # optional
ADMIN_API_KEY=lexai-admin-secret

# 3. Start backend
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# 4. Seed data
python scripts/seed_raw_data.py

# 5. Start frontend
cd "lexai-–-trợ-lý-pháp-lý-thông-minh UI"
npm install && npm run dev
# → http://localhost:3000
# → http://localhost:3000/admin/login (key: lexai-admin-secret)
```
