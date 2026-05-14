# Multilingual Upgrade — Session Log

**Dự án:** Universal Legal Knowledge Assistant  
**Phạm vi:** Nâng cấp pipeline Legal GraphRAG hỗ trợ đa ngôn ngữ (Tiếng Việt + Tiếng Anh)  
**Ngày:** 14/05/2026

---

## Mục tiêu

Thêm khả năng đa ngôn ngữ đầy đủ vào pipeline Legal Multimodal GraphRAG, đáp ứng 10 yêu cầu kỹ thuật:

1. Phát hiện ngôn ngữ chính thức với điểm tin cậy và thẩm quyền pháp lý (jurisdiction)
2. Chuẩn hóa thuật ngữ pháp lý (Điều → article, Khoản → clause, Mục → section)
3. Chuẩn hóa truy vấn: "Article 1", "Art. 1", "Điều 1", "ARTICLE I" → `article_1`
4. Engine truy xuất đa ngôn ngữ (4 lượt: canonical_ref → alias_keyword → keyword → semantic)
5. Smoke test đa ngôn ngữ sinh từ cấu trúc tài liệu
6. Canonical ID trên mọi đơn vị cấu trúc pháp lý
7. Cạnh ALIAS_OF trong đồ thị cho tham chiếu chéo ngôn ngữ
8. Metadata chunk nâng cấp với `language`, `canonical_refs`, `hierarchy_path`
9. Debug log truy xuất theo từng truy vấn
10. Chỉ số đánh giá đa ngôn ngữ trong báo cáo JSON và Markdown

**Ràng buộc:** Không viết lại extraction từ đầu, không xóa pipeline stages, không hardcode ngôn ngữ, không phá vỡ báo cáo hiện có.

---

## Các file đã tạo mới

### `src/retrieval/`

| File | Mô tả |
|------|-------|
| `__init__.py` | Package init |
| `language_detector.py` | Phát hiện ngôn ngữ (VI/EN) với điểm tin cậy, jurisdiction, tín hiệu diacritic + từ khóa pháp lý |
| `legal_aliases.py` | Bảng alias đa ngôn ngữ: `điều ↔ article`, `khoản ↔ clause`, `mục ↔ section`, v.v. |
| `query_normalizer.py` | Chuẩn hóa truy vấn: "Điều 3" → `article_3`, số La Mã → số Ả Rập |
| `canonical_references.py` | `CanonicalRefBuilder` — tạo ID ổn định (`article_1`, `clause_3_a`) cho mọi đơn vị cấu trúc |
| `retrieval_engine.py` | `RetrievalEngine` — 4 lượt tìm kiếm + debug log per truy vấn |

### `src/graphrag/`

| File | Mô tả |
|------|-------|
| `__init__.py` | Package init |
| `legal_ontology.py` | `OntologyEnricher` — thêm cạnh ALIAS_OF giữa các node chia sẻ canonical_ref |

### `src/evaluation/`

| File | Mô tả |
|------|-------|
| `multilingual_metrics.py` | Tính chỉ số đa ngôn ngữ: độ phủ canonical_ref, tỷ lệ hit cross-lang, phân phối ngôn ngữ |

### `src/utils/`

| File | Mô tả |
|------|-------|
| `compat.py` | `BaseModel` fallback khi Pydantic không được cài — hỗ trợ keyword-init và `model_dump()` đệ quy |

---

## Các file đã sửa đổi

| File | Thay đổi |
|------|---------|
| `src/schemas/document.py` | Thêm class `LanguageDetection`, field `language_detection` vào `DocumentProfile` |
| `src/schemas/chunk.py` | Thêm `language`, `canonical_refs`, `hierarchy_path` vào `Chunk` |
| `src/schemas/graph.py` | Thêm `"ALIAS_OF"` vào `EDGE_TYPES`, hằng `ALIAS_EDGES`; viết lại `BaseModel` fallback |
| `src/schemas/evaluation.py` | Thêm `MultilingualMetrics`, field `multilingual_metrics` vào `DocumentEvalResult` |
| `src/pipeline/stages.py` | Wire phát hiện ngôn ngữ, canonical refs, alias edges; nâng cấp smoke test đa ngôn ngữ |
| `src/pipeline/orchestrator.py` | Thêm `_build_multilingual_metrics()`, truyền vào `DocumentEvalResult` |
| `src/evaluation/reports.py` | Thêm section "Multilingual Metrics" vào báo cáo Markdown |

---

## Vấn đề đã giải quyết

### 1. File `language_detector.py` bị truncate (blocking)
**Nguyên nhân:** Công cụ `Write` cắt ngắn file ở dòng 382, để lại syntax error `if en_avg >= vi_avg + DOMINAN` (thiếu `CE:`).  
**Giải pháp:** Dùng `bash` để ghi lại toàn bộ file thông qua Python heredoc, tránh công cụ `Write` gây truncation.

### 2. `BaseModel = object` không hỗ trợ keyword arguments
**Nguyên nhân:** Khi Pydantic không được cài, các schema dùng `BaseModel = object` khiến `GraphNodeProvenance(document_id="")` ném `TypeError: takes no arguments`.  
**Giải pháp:** Tạo `src/utils/compat.py` với `BaseModel` fallback đầy đủ — nhận `**kwargs`, copy default từ class hierarchy, `model_dump()` đệ quy.

### 3. `.pyc` cache cũ ghi đè file `.py` đã sửa
**Nguyên nhân:** File `.py` trên Windows filesystem mount có timestamp cũ hơn `.pyc` trên Linux, khiến Python dùng cache cũ.  
**Giải pháp:** `touch` các file `.py` để cập nhật modification time, buộc Python biên dịch lại.

### 4. `graph.py` bị truncate sau khi sửa `BaseModel`
**Nguyên nhân:** `Edit` tool cũng bị truncation, để lại `GraphSubgraph` với docstring chưa đóng.  
**Giải pháp:** Viết lại toàn bộ `graph.py` qua `bash cat >`.

### 5. `SyntaxWarning: invalid escape sequence` trong `language_detector.py`
**Nguyên nhân:** Bash ghi file dùng `\b` và `\s` trong string thường (không phải raw string). Python hiểu `"\b"` là ký tự backspace (ASCII 8), `"\s"` sinh `SyntaxWarning`.  
**Giải pháp:** Viết lại patterns với `"\\b..."` và `"\\s"` (double backslash) trong string thường, dùng `r"..."` raw string cho patterns tiếng Anh.

### 6. `model_dump()` không serialize đệ quy
**Nguyên nhân:** Fallback `BaseModel.model_dump()` chỉ trả về `self.__dict__` thô, không convert nested `BaseModel` instances, gây `TypeError: Object of type DocumentEvalResult is not JSON serializable`.  
**Giải pháp:** Thêm hàm `_to_jsonable()` đệ quy trong `compat.py`.

### 7. `make_edge_id()` gọi không có tham số trong `legal_ontology.py`
**Nguyên nhân:** Bug khi viết — hàm cần `(from_id, edge_type, to_id)` nhưng gọi rỗng.  
**Giải pháp:** Sửa thành `make_edge_id(n1.node_id, _ALIAS_OF, n2.node_id)`.

---

## Vấn đề đang giải quyết

### Trích xuất `.doc` thất bại trên Windows
**Triệu chứng:**
```
⚠️ Could not extract text from '106_2025_QH15_628717.doc'.
   Install docx2txt or antiword for .doc support.
```
**Nguyên nhân:** File `.doc` nhị phân OLE (format cũ). Pipeline thử 3 phương pháp:
1. `docx2txt` — không được cài
2. `antiword` — không có trên Windows
3. `python-docx` — chỉ đọc `.docx`, không đọc `.doc` nhị phân

**Giải pháp đề xuất tiếp theo:** Thêm Attempt 4 dùng `win32com.client` (Word COM Automation trên Windows) vào `_read_doc_text()` trong `stages.py`:

```python
# Attempt 4: win32com Word COM (Windows only, requires Microsoft Word)
try:
    import win32com.client
    import pythoncom
    pythoncom.CoInitialize()
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(path.resolve()))
    text = doc.Range().Text
    doc.Close(False)
    word.Quit()
    if text.strip():
        return text
except Exception:
    pass
```

Hoặc thử LibreOffice headless nếu Word không được cài:
```bash
soffice --headless --convert-to txt:Text --outdir /tmp/ document.doc
```

---

## Kết quả kiểm thử

Chạy với `--input ./samples` (file HTML mẫu):

```
✅ OVERALL: PASS
  Processed : 2 documents
  Passed    : 2
  Warnings  : 0
  Failed    : 0
  Duration  : 0.40s
```

### English document (`sample_contract.html`)
- Language: `en` (confidence 0.75)
- Canonical refs: 28, ALIAS_OF edges: 20
- Cross-lang hit rate: **100%** (`Điều 1` → tìm thấy article tiếng Anh)

### Vietnamese document (`sample_hop_dong_viet.html`)
- Language: `vi` (confidence 0.50), Jurisdiction: `VN`
- Canonical refs: 31, ALIAS_OF edges: 20
- Cross-lang hit rate: **100%** (`Article 1` → tìm thấy điều khoản tiếng Việt)

Chạy với `--input ./raw_data` (file `.doc` thực tế — Luật 106/2025/QH15, Luật 45/2019/QH14):
```
❌ OVERALL: FAIL
  Failed: 2 (không trích xuất được text từ file .doc nhị phân)
```

---

## Bước tiếp theo

1. **[Ưu tiên cao]** Fix `.doc` extraction — thêm `win32com.client` (hoặc LibreOffice) vào `_read_doc_text()` để đọc file nhị phân OLE trên Windows
2. Chạy lại pipeline với file `.doc` thực tế và xác nhận PASS
3. Kiểm tra báo cáo Markdown với dữ liệu Vietnamese legal (Luật Doanh nghiệp, Bộ luật Dân sự, v.v.)
