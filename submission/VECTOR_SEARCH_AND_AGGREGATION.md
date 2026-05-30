# Vector Search & Aggregation Pipeline — LexAI / ULKA

---

## 1. Tại sao cần Vector Search?

Pháp luật Việt Nam có đặc thù:
- Người dùng hỏi bằng ngôn ngữ tự nhiên, không biết tên điều luật
- Cùng một khái niệm có nhiều cách diễn đạt: "sổ đỏ" = "GCN QSDĐ" = "giấy chứng nhận quyền sử dụng đất"
- Câu hỏi ngắn, không dấu: "so do bi tranh chap phai lam gi"

**Keyword exact match** không đủ. Vector Search tìm được văn bản **gần nghĩa**, ngay cả khi không có từ nào trùng.

---

## 2. Embedding Model

| Thuộc tính | Giá trị |
|---|---|
| Model | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| Dimension | 384 |
| Languages | Đa ngôn ngữ (Vietnamese, English) |
| Metric | Cosine similarity |
| Latency | ~5–15ms per query (CPU) |
| Threshold | 0.55 (kết quả dưới ngưỡng bị loại) |

Embedding được tạo tại:
- **Ingestion time:** `src/pipeline/embedding_stage.py → embed_chunks_into_mongo()`
- **Query time:** `src/engine/retrieval_fusion.py → embed_text(query_variant)`

---

## 3. Vector Search Index

### Index Definition (Atlas Search Index)

```json
{
  "name": "chunk_embedding_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 384,
        "similarity": "cosine"
      },
      {
        "type": "filter",
        "path": "user_id"
      },
      {
        "type": "filter",
        "path": "is_global"
      },
      {
        "type": "filter",
        "path": "law_type"
      }
    ]
  }
}
```

Collection: `chunks_vec`  
Database: `legal_knowledge_assistant`

---

## 4. Aggregation Pipeline — Vector Search

### 4.1 Baseline Pipeline (Domain-filtered)

```javascript
// src/mongodb/mongo_storage.py → vector_search_chunks()
db.chunks_vec.aggregate([
  {
    $vectorSearch: {
      index: "chunk_embedding_index",
      path: "embedding",
      queryVector: queryEmbedding,      // 384-dim float array
      numCandidates: 100,               // ANN search pool size
      limit: 20,                        // return top 20 before filtering
      filter: {
        $or: [
          { user_id: userId },
          { is_global: true }
        ]
      }
    }
  },
  {
    $addFields: {
      vector_score: { $meta: "vectorSearchScore" }
    }
  },
  {
    $match: {
      vector_score: { $gte: 0.55 }     // FUSION_VECTOR_SIGNAL_THRESHOLD
    }
  },
  {
    $project: {
      chunk_id: 1,
      content: 1,
      law_type: 1,
      law_reference: 1,
      vector_score: 1,
      is_global: 1,
      metadata: 1
    }
  },
  {
    $sort: { vector_score: -1 }
  },
  {
    $limit: 10
  }
])
```

### 4.2 Domain-Specific Pipeline (Dat_dai example)

```javascript
db.chunks_vec.aggregate([
  {
    $vectorSearch: {
      index: "chunk_embedding_index",
      path: "embedding",
      queryVector: queryEmbedding,
      numCandidates: 150,
      limit: 30,
      filter: {
        $and: [
          { $or: [{ user_id: userId }, { is_global: true }] },
          { law_type: "dat_dai" }       // domain-specific filter
        ]
      }
    }
  },
  {
    $addFields: {
      vector_score: { $meta: "vectorSearchScore" }
    }
  },
  {
    $match: { vector_score: { $gte: 0.55 } }
  },
  {
    $project: {
      chunk_id: 1,
      content: { $substr: ["$content", 0, 500] },  // truncate for performance
      law_type: 1,
      law_reference: 1,
      vector_score: 1
    }
  },
  {
    $sort: { vector_score: -1 }
  },
  {
    $limit: 10
  }
])
```

---

## 5. Hybrid Retrieval Fusion

Vector search chỉ là 1 trong 4 tín hiệu. `RetrievalFusionEngine` kết hợp:

```
FusionScore = 0.45 × vector_signal
            + 0.20 × bm25_signal
            + 0.25 × graph_signal
            + 0.10 × behavior_signal
```

### 5.1 Signal 1 — Vector (weight 0.45)

MongoDB `$vectorSearch` cosine similarity. Kết quả được min-max normalize về [0,1].

### 5.2 Signal 2 — BM25 Keyword (weight 0.20)

TF-based keyword density (không cần corpus IDF):

```python
score = sum(query_terms in chunk) / len(chunk_tokens) * 20
```

Ưu điểm: hoạt động kể cả khi vector index không available.

### 5.3 Signal 3 — Graph Expanded (weight 0.25)

BFS traversal từ law-reference nodes được trích xuất từ query:

```python
# Ví dụ: query chứa "Điều 202 Luật Đất đai"
# → seed BFS từ node "luat_dat_dai_2013:dieu_202"
# → expand qua edges OVERRIDES, AMENDS, CITES (depth ≤ 3)
# → boost chunks có law_reference trùng với expanded nodes
```

Edge weights:
```
OVERRIDES(0.92) > INVALIDATES(0.90) > CONFLICTS_WITH(0.88)
AMENDS(0.85) > CITES(0.85) > REQUIRES(0.82) > DEPENDS_ON(0.78)
```

Depth penalty: -0.10 per BFS level.

### 5.4 Signal 4 — Behavior (weight 0.10)

Collaborative filter từ `interactions` collection — boost chunks từ documents người dùng đã tương tác (view/save/download). Half-life decay: `exp(-0.08 * days)`.

### 5.5 Normalization và Deduplication

```python
# Với mỗi signal:
min_s, max_s = min(scores), max(scores)
normalized = [(s - min_s) / (max_s - min_s + 1e-9) for s in scores]

# Dedup by chunk_id:
seen = {}
for result in all_results:
    if result.chunk_id in seen:
        # max merge: take best score per signal
        seen[result.chunk_id] = merge(seen[result.chunk_id], result)
    else:
        seen[result.chunk_id] = result

# Fusion:
result.fusion_score = (
    0.45 * result.vector_score +
    0.20 * result.bm25_score +
    0.25 * result.graph_score +
    0.10 * result.behavior_score
)
```

---

## 6. Aggregation Pipeline — Behavior Analytics

Dùng aggregation để tính behavior profile cho recommendations:

```javascript
// Tính top domains của user
db.interactions.aggregate([
  { $match: { user_id: userId } },
  { $group: {
    _id: "$law_type",
    count: { $sum: 1 },
    last_seen: { $max: "$timestamp" }
  }},
  { $sort: { count: -1 } },
  { $limit: 5 }
])
```

```javascript
// Tính law_type distribution
db.chunks_vec.aggregate([
  { $match: { is_global: true } },
  { $group: {
    _id: "$law_type",
    chunk_count: { $sum: 1 }
  }},
  { $sort: { chunk_count: -1 } }
])
```

---

## 7. Aggregation Pipeline — Reporting / Release Gate

```javascript
// Đếm fallback/demo rate
db.interactions.aggregate([
  { $match: { event_type: "situation_analysis" } },
  { $group: {
    _id: "$is_demo",
    count: { $sum: 1 }
  }}
])
// → { _id: true, count: 150 }  // demo hits
// → { _id: false, count: 0 }   // real vector hits (0 vì thiếu case_embedding_index)
```

---

## 8. Similar Cases — Fallback Pipeline

Khi `case_embedding_index` không tồn tại (Atlas M0 limit):

```python
# src/mongodb/mongo_storage.py → find_similar_cases()

try:
    # Attempt vector search
    results = db.legal_cases.aggregate([
        { "$vectorSearch": {
            "index": "case_embedding_index",
            ...
        }}
    ])
except OperationFailure:
    # Fallback: keyword filter + manual scoring
    results = db.legal_cases.find({
        "domain": detected_domain,
        "is_demo": True
    }).limit(3)
    # Mark results with is_demo=True
```

Frontend hiển thị badge "Ví dụ tham khảo" khi `is_demo=True` — **không bao giờ giả mạo là kết quả thật**.

---

## 9. Threshold Policy

| Threshold | Giá trị | Áp dụng cho |
|---|---|---|
| `FUSION_VECTOR_SIGNAL_THRESHOLD` | 0.55 | Loại vector hits dưới ngưỡng |
| Env override | `FUSION_VECTOR_SIGNAL_THRESHOLD=0.60` | Production tuning |
| BM25 minimum | 0.0 (không filter) | BM25 always contributes |
| Fusion minimum | 0.0 (không filter) | Final ranking bao gồm tất cả |

**Hard constraint:** Score threshold 0.55 là giá trị cố định, không được thay đổi để inflate benchmark.

---

## 10. Hạn chế và Roadmap

### Hạn chế hiện tại

| Issue | Root cause | Workaround |
|---|---|---|
| `case_embedding_index` không tồn tại | Atlas M0 max 3 vector indexes | Demo fallback với is_demo=True badge |
| `clause_embedding_index` không tồn tại | Cùng lý do | Text-based clause search |
| avg_top1_score = 0.52 | Atlas M0 không tạo được full vector search → fallback trả score cố định 0.50 | Hiểu là infra artifact, không phải model kém |

### Cách phát hiện blocker

Release gate script tự động phát hiện:
```
❌ fallback_demo_rate_pct: 100.0 > 30.0 (target)
```

Hệ thống **không cố giấu** limitation này. Score 0.50 cố định từ demo fallback được ghi rõ trong `is_fallback=True` field của benchmark results.

### Roadmap

1. **Upgrade Atlas M10+** → tạo `case_embedding_index` → GA gate PASS
2. **Hybrid retrieval expansion** — thêm BM25 corpus-level IDF để cải thiện keyword signal
3. **Reranking expansion** — thêm cross-encoder reranker sau retrieval fusion
