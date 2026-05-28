# TÀI LIỆU KỸ THUẬT: HỆ THỐNG TRỢ LÝ PHÁP LÝ THÔNG MINH LEXAI

> **Tên Giải Pháp**: LexAI — Universal Legal Knowledge Assistant (ULKA)
> **Cơ sở Công Nghệ**: FastAPI Backend + React/TS Frontend + MongoDB Atlas (Vector Search & Aggregation Pipeline) + Multimodal GraphRAG + local SentenceTransformers.

---

## 1. MVP VÀ KIẾN TRÚC HỆ THỐNG TỔNG THỂ

### 1.1. Khái quát Use-case & Giải pháp
Trong bối cảnh hệ thống văn bản pháp luật Việt Nam thường xuyên cập nhật và phân mảnh (Luật, Nghị định, Thông tư chồng chéo), người dân và doanh nghiệp gặp rất nhiều khó khăn để tìm kiếm câu trả lời pháp lý chính xác và tự đánh giá rủi ro khi giao dịch. 

**LexAI** giải quyết bài toán này bằng cách cung cấp một trợ lý chuyên sâu hoạt động như một chuyên gia tư vấn pháp lý kỹ thuật số:
1. **Phân tích Tình huống tự động**: Nhận diện lĩnh vực pháp lý, chấm điểm vị thế pháp lý của người dùng, phân tích và trích dẫn điều luật chính xác.
2. **Rà soát Hợp đồng thông minh**: Quét tệp tin hợp đồng tải lên (PDF/DOCX/DOC), tự động tìm kiếm rủi ro và các điều khoản thiếu hụt so với mẫu chuẩn.
3. **Đề xuất Hành động Phù hợp Tiếp theo (Next Best Actions)**: Đưa ra lộ trình hành động được cá nhân hóa dựa trên rủi ro vụ việc của người dùng.
4. **Dashboard Phân tích Hành vi**: Biểu diễn trực quan hóa quá trình tương tác và các lĩnh vực pháp lý người dùng quan tâm qua Recharts và Recommender Engine.

### 1.2. Sơ đồ Kiến trúc Hệ thống (System Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VITE FRONTEND (React & TS)                      │
│   - Dashboard & Recharts         - Interactive Case Journey Timeline   │
│   - Context Retention (sessionStorage)  - Contract Document Viewer     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Requests
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND RUNTIME                        │
│   - Situation Classifier         - Next Best Action Engine             │
│   - Pipeline Processor (Local Extractor & Structure-based Chunker)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          ▼ PyMongo (Driver)                                  ▼ SentenceTransformers
┌───────────────────────────────────┐               ┌────────────────────┐
│          MONGODB ATLAS            │               │ EMBEDDING STAGE    │
│  - Document Store                 │               │ - local model:     │
│  - Vector Search Index            │               │ paraphrase-        │
│  - Behavioral Interaction Logs    │               │  multilingual-     │
│  - Cache & Metadata               │               │  MiniLM-L12-v2     │
└───────────────────────────────────┘               └────────────────────┘
```

---

## 2. DATA SCHEMA VÀ KIẾN TRÚC DỮ LIỆU MONGODB

Hệ thống được thiết kế với mô hình dữ liệu phi quan hệ (NoSQL) chuẩn hóa trong MongoDB nhằm tối ưu hóa tốc độ truy vấn, tìm kiếm ngữ nghĩa và tích hợp tính năng cá nhân hóa hành vi.

### 2.1. Các Collection Chính và Trường Dữ liệu (Schemas)

#### 1. Collection: `legal_cases` (Lưu trữ kho vụ án và tình huống thực tế)
```json
{
  "_id": "ObjectId",
  "case_id": "string (unique)",
  "title": "string (Tiêu đề vụ việc)",
  "law_type": "string (Lĩnh vực: dat_dai, hop_dong, lao_dong...)",
  "situation_summary": "string (Mô tả chi tiết tình huống)",
  "legal_issues": ["string (Các vấn đề pháp lý phát hiện)"],
  "outcome": "string (Kết quả phân xử)",
  "result": "string (Bài học rút ra)",
  "key_laws": ["string (Các căn cứ luật áp dụng)"],
  "embedding": [ "float (384 chiều)" ],
  "priority": "int (Trọng số hiển thị)",
  "updated_at": "ISODate"
}
```

#### 2. Collection: `contract_clauses` (Kho lưu trữ điều khoản hợp đồng mẫu chuẩn)
```json
{
  "_id": "ObjectId",
  "clause_id": "string",
  "doc_id": "string",
  "user_id": "string",
  "clause_text": "string (Nội dung điều khoản mẫu)",
  "clause_type": "string (Loại: termination, penalty, force_majeure...)",
  "risk_level": "string (low, medium, high, critical)",
  "suggestion": "string (Hướng dẫn điều chỉnh điều khoản)",
  "embedding": [ "float (384 chiều)" ],
  "updated_at": "ISODate"
}
```

#### 3. Collection: `chunks_vec` (Kho lưu trữ các mảnh cắt điều luật để chạy GraphRAG)
```json
{
  "_id": "ObjectId",
  "chunk_id": "string (unique)",
  "doc_id": "string",
  "user_id": "string",
  "content": "string (Nội dung trích dẫn chi tiết của Điều luật)",
  "embedding": [ "float (384 chiều - Tùy chọn)" ],
  "is_global": "boolean (Quy định văn bản luật chung của hệ thống)",
  "metadata": {
    "chunk_type": "string",
    "law_type": "string",
    "canonical_refs": ["string"],
    "language": "string",
    "confidence": "float"
  },
  "created_at": "ISODate"
}
```

#### 4. Collection: `interactions` (Ghi nhận hành vi để chạy công cụ đề xuất Collaborative Filtering)
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "doc_id": "string",
  "action_type": "string (view, save, download, situation_analysis, nba_click)",
  "chunk_id": "string (Tùy chọn)",
  "context": {
    "law_type": "string",
    "situation_snippet": "string"
  },
  "timestamp": "string (ISO Format)"
}
```

#### 5. Collection: `user_profiles` (Lịch sử tổng hợp hành vi người dùng)
```json
{
  "_id": "ObjectId",
  "user_id": "string (unique)",
  "law_type_weights": {
    "dat_dai": "float [0.0 - 1.0]",
    "hop_dong": "float [0.0 - 1.0]",
    "lao_dong": "float [0.0 - 1.0]"
  },
  "action_frequencies": {
    "view": "int",
    "download": "int"
  },
  "active_hours": ["int (Các khung giờ hoạt động thường xuyên)"],
  "total_interactions": "int",
  "days_active": "int",
  "top_law_type": "string",
  "last_active_iso": "string"
}
```

---

## 3. MÔ TẢ CÁCH ÁP DỤNG VECTOR SEARCH VÀ AGGREGATION PIPELINE

### 3.1. Áp dụng MongoDB Atlas Vector Search
Mục tiêu là thực hiện **tìm kiếm ngữ nghĩa tiếng Việt** trên toàn bộ văn bản điều luật (`chunks_vec`), vụ việc tương tự (`legal_cases`), và điều khoản hợp đồng (`contract_clauses`).

#### 3.1.1. Cấu hình Index Tìm kiếm Vector (Atlas Search Index)
Index được cấu hình trên trường `embedding` sử dụng thuật toán **kNN** với hàm đo khoảng cách **Cosine** (384 chiều):
```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 384,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

#### 3.1.2. Vector Search Pipeline trong Python (Ví dụ tìm kiếm vụ việc)
```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "case_embedding_index",
            "path": "embedding",
            "queryVector": query_vector, # Sinh ra từ MiniLM-L12-v2
            "numCandidates": limit * 10,
            "limit": limit * 2,
        }
    },
    {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
    {"$match": {"law_type": "dat_dai"}}, # Lọc theo lĩnh vực đã nhận diện
    {"$limit": limit},
    {"$project": {"_id": 0, "embedding": 0}}
]
results = list(db.legal_cases.aggregate(pipeline))
```

#### 3.1.3. Cơ chế Dự phòng Keyword Fallback thông minh (Sáng tạo kỹ thuật)
Do MongoDB Atlas Free Tier (M0) hoặc môi trường mạng đôi khi không hỗ trợ Vector Search, hệ thống của chúng tôi được thiết kế với cơ chế dự phòng tự động (Graceful Fallback). Nếu Vector Search gặp lỗi, hệ thống lập tức kích hoạt biểu thức chính quy (Regex Text Matching) để trả về các vụ việc khớp từ khóa nhanh chóng:
```python
def keyword_search_cases(self, keywords: List[str], limit: int = 5):
    pattern = "|".join(keywords)
    return list(self.legal_cases.find({
        "$or": [
            {"situation_summary": {"$regex": pattern, "$options": "i"}},
            {"title": {"$regex": pattern, "$options": "i"}}
        ]
    }, {"_id": 0, "embedding": 0}).limit(limit))
```

---

### 3.2. Áp dụng MongoDB Aggregation Pipelines
Aggregation Pipelines được sử dụng làm lõi phân tích hành vi của hệ thống để vẽ nên **Dashboard tương tác** thông minh và thực tế của người dùng.

#### 3.2.1. Pipeline Tính toán Trọng số Lĩnh vực người dùng quan tâm (Attention Weights)
Pipeline này phân tích lịch sử tương tác của người dùng (`interactions`), đếm số lượt và chuẩn hóa trọng số theo hệ số giảm dần thời gian (Recency Exponential Decay Factor) để tìm ra các lĩnh vực người dùng đang quan tâm nhất:

```python
pipeline = [
    {"$match": {"user_id": user_id}},
    # Lấy các tương tác có ranh giới thời gian 60 ngày gần nhất
    {"$addFields": {
        "days_ago": {
            "$divide": [
                {"$subtract": [datetime.now(timezone.utc), {"$toDate": "$timestamp"}]},
                86400000 # Chuyển đổi mili-giây sang ngày
            ]
        }
    }},
    # Tính toán exponential decay factor (e^-0.05*t)
    {"$addFields": {
        "weight": {"$exp": {"$multiply": [-0.05, "$days_ago"]}}
    }},
    # Nhóm theo lĩnh vực pháp lý và tính tổng trọng số
    {"$group": {
        "_id": "$context.law_type",
        "total_weight": {"$sum": "$weight"}
    }},
    {"$sort": {"total_weight": -1}}
]
```

#### 3.2.2. Pipeline Tính toán Khung giờ hoạt động tích cực (Active Hours)
Được sử dụng để vẽ biểu đồ và cá nhân hóa thời gian gửi thông báo pháp lý phù hợp:
```python
pipeline = [
    {"$match": {"user_id": user_id}},
    {"$project": {
        "hour": {"$hour": {"$toDate": "$timestamp"}}
    }},
    {"$group": {
        "_id": "$hour",
        "count": {"$sum": 1}
    }},
    {"$sort": {"count": -1}},
    {"$limit": 5}
]
```

#### 3.2.3. Pipeline Đề xuất Đồng nghiệp (Peer-trending Recommendations)
Tích hợp thuật toán đề xuất cộng tác (Collaborative Filtering) để tìm những tài liệu mà những người dùng khác có cùng hồ sơ quan tâm đang truy cập tích cực:
```python
# 1. Tìm những người dùng có cùng mối quan tâm hàng đầu (Top law_type)
similar_users_pipeline = [
    {"$match": {"user_id": {"$ne": user_id}, "context.law_type": top_law_type}},
    {"$group": {"_id": "$user_id", "interaction_count": {"$sum": 1}}},
    {"$sort": {"interaction_count": -1}},
    {"$limit": 10}
]
# 2. Lấy ra danh sách tài liệu/vụ án thịnh hành nhất của nhóm tương đồng này
trending_docs_pipeline = [
    {"$match": {"user_id": {"$in": peer_user_ids}, "action_type": {"$in": ["download", "save"]}}},
    {"$group": {
        "_id": "$doc_id",
        "trending_score": {"$sum": 1}
    }},
    {"$sort": {"trending_score": -1}},
    {"$limit": 5}
]
```

---

## 4. KẾT LUẬN

Giải pháp **LexAI** chứng minh sự kết hợp hoàn hảo giữa **FastAPI RAG System** và các tính năng nâng cao của **MongoDB (Vector Search & Aggregation Pipeline)**. 

Bằng cách sử dụng Vector Search để tìm kiếm ngữ nghĩa văn bản pháp luật, tích hợp dự phòng Keyword Fallback và áp dụng triệt để Aggregation Pipelines để xây dựng Recommender Engine cá nhân hóa, LexAI là một MVP hoàn chỉnh, có kiến trúc mở rộng mạnh mẽ và tiềm năng đóng góp cực kỳ lớn cho cộng đồng trong việc phổ biến pháp luật Việt Nam.
