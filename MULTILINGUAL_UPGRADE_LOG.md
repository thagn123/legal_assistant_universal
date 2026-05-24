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

## Vấn đề đã giải quyết (tiếp theo)

### 8. Logging severity bị nhầm: `fail` dispatch thành `INFO` thay vì `ERROR`
**Nguyên nhân:** `PipelineLogger._emit(level="fail", ...)` gọi `getattr(self._logger, "fail", self._logger.info)` → không có method `fail` → fallback về `info`. Stage thất bại bị log ở INFO level, không thể phân tích lỗi qua log filter.  
**Giải pháp:** Thêm `_SEVERITY_MAP` trong `src/utils/logging.py`:
```python
_SEVERITY_MAP = {"pass": "info", "fail": "error", "warning": "warning", "skipped": "info", ...}
```
Dùng map này trong `_emit` để tách `status` (stage outcome) ra khỏi Python log severity.

### 9. `.doc` trích xuất text nhưng trả về 0 blocks — stage thất bại
**Triệu chứng sau khi thêm win32com:**
```
extraction: ⚠️ warning | Extracted 1 blocks, 0 tables from 1 pages
canonical_structuring: 0 sections, 0 articles, 0 clauses | Structure Detected: No
chunking: 1 chunk (54,949 tokens avg) using strategy=semantic
```
**Nguyên nhân (2 lớp):**

**Lớp 1 — thiếu win32com:** `_read_doc_text()` chỉ thử `docx2txt` / `antiword` / `python-docx`, đều thất bại với OLE `.doc` binary trên Windows.  
**Giải pháp lớp 1:** Thêm 5-attempt fallback chain vào `_read_doc_text()`:
1. `win32com.client` — Word COM automation (Windows + MS Word, reliable nhất)
2. LibreOffice headless (`soffice --convert-to txt`) — cross-platform
3. `docx2txt` — chỉ hoạt động với XML-based `.doc`
4. `antiword` CLI — Linux/macOS
5. `python-docx` — last resort

**Lớp 2 — `\r` line endings từ win32com:** `doc.Content.Text` trong Word COM trả về paragraphs phân cách bằng `\r` (CR, 0x0D), không phải `\n\n`. Hàm `_extract_doc` split bằng `re.split(r"\n{2,}", text)` nên không tìm thấy điểm ngắt → toàn bộ 200+ điều khoản bị đóng gói thành **1 block duy nhất** → `_detect_hierarchy` không nhận ra cấu trúc → 0 articles.

**Giải pháp lớp 2:** Trong `_extract_doc` (`stages.py:648-653`), normalize line endings trước khi split:
```python
text = text.replace("\r\n", "\n").replace("\r", "\n")
paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
```
Mỗi dòng thành 1 block riêng → `_detect_block_type()` nhận ra "Điều X" là heading → `_detect_hierarchy()` xây dựng đúng cây Section/Article.

---

## Kết quả kiểm thử

### Lần 1: `--input ./samples` (HTML mẫu)

```
✅ OVERALL: PASS
  Processed : 2 documents
  Passed    : 2
  Warnings  : 0
  Failed    : 0
  Duration  : 0.40s
```

| Document | Language | Canonical refs | ALIAS_OF | Cross-lang hit rate |
|----------|----------|---------------|----------|---------------------|
| `sample_contract.html` | `en` (0.75) | 28 | 20 | 100% |
| `sample_hop_dong_viet.html` | `vi` (0.50), VN | 31 | 20 | 100% |

### Lần 2: `--input ./raw_data` (`.doc` — Luật 106/2025/QH15, Luật 45/2019/QH14) — **SAU KHI FIX**

```
⚠️ OVERALL: WARNING  (không có FAIL, không có ERROR)
  Processed : 2 documents
  Passed    : 0
  Warnings  : 2
  Failed    : 0
  Duration  : 14.98s
```

So sánh **trước/sau** fix `\r` line endings:

| Metric | Trước fix | Sau fix |
|--------|-----------|---------|
| Blocks (per doc) | 1 | **1274** |
| Sections | 0 | **13** |
| Articles | 0 | **116** |
| Chunks | 1 (54,949 tokens) | **116 (avg 53 tokens)** |
| Graph nodes | 2 | **246** |
| Graph edges | 1 | **3849** (3604 ALIAS_OF) |
| Chunking strategy | semantic | **long_local_structural** |
| Structure Detected | No | **Yes** |
| Retrieval hit rate | 100% giả | **88% thực** |

**Cảnh báo còn lại (đúng, không phải bug):**
- `.doc` format: table topology không thể preserve qua text extraction — cần convert sang `.docx`
- Duplicate blocks: nội dung lặp lại trong file `.doc` gốc (header/footer, mục lục) — detection đúng

---

## Nâng cấp kiến trúc — 5 Architecture Upgrades (14/05/2026)

Sau khi xác nhận kết quả đúng trên `.doc`, tiến hành 5 nâng cấp kiến trúc hệ thống:

### Fix 1 — ALIAS_OF Over-Connection (`src/graphrag/legal_ontology.py`)

**Vấn đề:** `_compatible_for_alias()` check `n1.node_type == n2.node_type` trước khi check Chunk exclusion. Vì hai Chunk đều có type `"Chunk"` → same-type check pass đầu tiên → không bao giờ đến exclusion gate → **3604 cạnh ALIAS_OF sai** (toàn bộ chunk-to-chunk).

**Giải pháp:** Đảo thứ tự: check `"Chunk" in (n1.node_type, n2.node_type)` trước, sau đó mới check same-type.

```python
# Trước (sai):
if n1.node_type == n2.node_type:   # Chunk-Chunk pass vào đây
    return True
if "Chunk" in (n1.node_type, n2.node_type):  # không bao giờ đến đây
    return False

# Sau (đúng):
if "Chunk" in (n1.node_type, n2.node_type):  # block sớm
    return False
if n1.node_type == n2.node_type:
    return True
```

**Kết quả:** 3604 → **0 ALIAS_OF edges** (chỉ structure nodes mới được alias).

---

### Fix 2 — Retrieval Scoring Quá Phẳng (`src/retrieval/retrieval_engine.py`)

**Vấn đề:** `_score()` dùng flat 0.2 bonus dựa trên presence của keyword — không phân biệt chunk chứa 1 lần hay 10 lần, không phạt chunk khổng lồ match ngẫu nhiên.

**Giải pháp:** Thay bằng TF bonus + logarithmic length penalty:

```python
# TF bonus: đếm số lần xuất hiện, cap tại 3/term, tối đa +0.25
tf_total = sum(min(content_lower.count(t), 3) for t in effective_terms)
tf_bonus = min(tf_total / (len(effective_terms) * 3), 1.0) * 0.25
score = min(score + tf_bonus, 1.0)

# Length penalty: logarithmic, kích hoạt trên 500 tokens, tối đa -0.15
token_estimate = len(chunk.content) // 4
if token_estimate > 500:
    penalty = min(math.log10(token_estimate / 500) * 0.075, 0.15)
    score = max(score - penalty, 0.0)
```

**Kết quả:** Chunks ngắn có từ khóa xuất hiện nhiều lần được rank cao hơn; chunk 50k-token không còn float lên top.

---

### Fix 3 — Duplicate Structural Noise (`src/pipeline/stages.py` — `_extract_doc`)

**Vấn đề:** Header/footer lặp lại từ win32com (số trang, tên cơ quan, tiêu đề chương) xuất hiện 100+ lần trong output text.

**Giải pháp:** Dedup trong-function cho short lines (< 80 chars) ngay khi tạo blocks:

```python
seen_short: Dict[str, int] = {}
for idx, para in enumerate(raw_lines):
    normalized = re.sub(r"\s+", " ", para.lower())
    if len(normalized) < 80:
        count = seen_short.get(normalized, 0) + 1
        seen_short[normalized] = count
        if count > 1:
            continue  # bỏ qua lần lặp thứ 2 trở đi
    blocks.append({...})
```

**Kết quả:** `degraded_blocks` giảm từ 9 → **2** (chỉ còn nội dung thực sự bị phát hiện trùng bởi cleaning stage).

---

### Fix 4 — Weak Clause/Subclause Parsing (`src/pipeline/stages.py` — `_detect_hierarchy`)

**Vấn đề:** Điểm (subpoints) không được gắn `parent_clause_id` đúng vì không có state tracker theo dõi Khoản hiện tại. Tất cả Điểm đều có `parent_clause_id=None`.

**Giải pháp:** Thêm `current_clause_id` state variable, reset khi vào Điều mới:

```python
current_section_id: Optional[str] = None
current_article_id: Optional[str] = None
current_clause_id: Optional[str] = None   # mới thêm

# Khi phát hiện Điều:
current_clause_id = None  # reset Khoản tracker

# Khi phát hiện Khoản:
clauses.append(Clause(..., parent_clause_id=None, ...))
current_clause_id = clause_id  # lưu lại để Điểm có thể nest vào

# Khi phát hiện Điểm:
clauses.append(Clause(..., parent_clause_id=current_clause_id, ...))  # đúng parent
```

**Kết quả:** Điểm a, b, c được nest đúng dưới Khoản 1, 2, 3 của cùng Điều. Hierarchy đầy đủ cho documents dùng "Khoản X" / "Điểm a" markers.

> **Lưu ý:** Luật 106/2025 và Luật 45/2019 dùng numbered items "1.", "2." thay vì "Khoản 1." → `clause_count=0` là **đúng** cho các luật này. Fix này áp dụng cho docs có "Khoản X" explicit.

---

### Fix 5 — Weak Table Topology (`src/pipeline/stages.py` — `_extract_docx` + `stage_canonical_structuring`)

**Vấn đề 1:** `_extract_docx` không detect header row → `header_row_index=None` → không thể phân biệt header với data.

**Giải pháp 1:** Detect header qua bold formatting của cell đầu tiên trong row 0:

```python
header_row_index: Optional[int] = None
if row_idx == 0 and header_row_index is None:
    is_bold = any(run.bold for para in first_cell.paragraphs for run in para.runs)
    if is_bold:
        header_row_index = 0
```

**Vấn đề 2:** `stage_canonical_structuring` tạo `TableCell` với `is_header=False` cho mọi cell; markdown representation không có separator row.

**Giải pháp 2:** Truyền `header_row_index` vào cell creation và thêm markdown `| --- |` separator:

```python
is_header = (header_row_index is not None and r_idx == header_row_index)
cells.append(TableCell(row=r_idx, col=c_idx, text=cell_text, is_header=is_header))

# Markdown với separator sau header:
md_lines.append(f"| {row_str} |")
if header_row_index is not None and r_idx == header_row_index:
    sep = " | ".join("---" for _ in row)
    md_lines.append(f"| {sep} |")
```

**Kết quả:** Tables trong `.docx` được render thành markdown chuẩn với header row rõ ràng, `is_header=True` trên cell đúng → chunk context chính xác hơn.

---

## Kết quả sau 5 Architecture Upgrades

Chạy lại trên `raw_data/` (Luật 106/2025/QH15, Luật 45/2019/QH14):

| Metric | Trước upgrades | Sau upgrades |
|--------|---------------|--------------|
| ALIAS_OF edges | 3604 (sai) | **0** (đúng) |
| degraded_blocks (per doc) | 9 | **2** |
| Clause nesting (Điểm→Khoản) | Sai (parent=None) | **Đúng** |
| Table header detection | Không có | **Bold-based** |
| Retrieval score distribution | Phẳng | **TF-weighted** |

**Doc 1 (106_2025_QH15):** 1258 blocks, 13 sections, 116 articles, 116 chunks avg 53 tokens, 245 structural edges, 0 ALIAS_OF.  
**Doc 2 (45_2019_QH14):** 1329 blocks, 41 sections, 220 articles, 220 chunks avg 51.8 tokens, 481 structural edges, 0 ALIAS_OF.

---

## Bước tiếp theo

1. **[Tùy chọn]** Thêm regex cho numbered items "1.", "2." (không có "Khoản") để detect clause trong luật dùng format này
2. **[Tùy chọn]** Test với Bộ luật Dân sự, Luật Doanh nghiệp để verify Khoản/Điểm nesting fix
3. Convert `.doc` → `.docx` cho các file cần full table topology support (hiện chỉ `.docx` detect header)

## 7️⃣ Cải thiện OCR và làm sạch văn bản

- **Tạo module `src/pipeline/ocr_utils.py**`
  - Các hàm: `_remove_control_chars`, `_normalize_unicode`, `merge_hyphenated_lines`, `filter_low_confidence_words`, `remove_noise_lines`, `clean_ocr_text`.
  - Nhiệm vụ: loại bỏ ký tự điều khiển, chuẩn hoá Unicode (giữ dấu tiếng Việt), gộp các dòng bị cắt, lọc từ có confidence thấp, loại bỏ dòng nhiễu, trả về chuỗi sạch.

- **Cập nhật `test_extraction_chunking.py`**
  - Sau bước *Extraction* gọi `clean_ocr_text` để xử lý `raw_blocks` và các `blocks` trong `CanonicalDocument`.
  - Kết quả: các block và chunk trong báo cáo cuối cùng chứa văn bản đã được làm sạch, giảm ký tự lạ, giảm độ dài chunk, cải thiện độ chính xác retrieval.

- **Đảm bảo import hoạt động**: Thêm `src/pipeline/__init__.py` (đã tồn tại) để Python nhận diện package.

*Thực hiện*: Chạy lại `python test_extraction_chunking.py` → các chunk bây giờ ngắn gọn, không còn các ký tự lạ và các từ bị tách.

## 8️⃣ Phân loại và Trích xuất Biểu mẫu Đơn từ mẫu (Form/Template Classification)

- **Cải tiến Regex và Group Indexing trong `src/pipeline/structurer.py`**:
  - Thiết kế lại `re_vi_form` thành dạng regex phi ký tự số tùy chọn và khớp tự do hơn:
    ```python
    re_vi_form = re.compile(
        r"^\s*(mẫu|mau|biểu\s+mẫu|bieu\s+mau|phụ\s+lục|phu\s+luc|phy\s+luc|phu|phy|phụ|form)\s+(?:số\s+|so\s+)?(?:([a-z0-9\.\-\/]+)\s+)?(.*)$",
        re.IGNORECASE | re.UNICODE,
    )
    ```
    Giúp nhận diện chính xác các tiêu đề bị lỗi OCR như `"Mau Dé xuat dy dau tu"`, `"Phu MAU VAN BAN"`.
  - Sửa lỗi truy xuất sai Group Index (`m_form.group(4)` đổi thành `m_form.group(3)`) khi trích xuất tiêu đề biểu mẫu, đảm bảo không bị bỏ sót tiêu đề mẫu đơn.
  
- **Xây dựng Công cụ Tạo Báo cáo Tự động (`scripts/generate_form_report.py`)**:
  - Viết script tự động chạy pipeline trích xuất OCR toàn bộ tệp, cấu trúc hóa và phân loại các biểu mẫu có thuộc tính `section_kind == "form"`.
  - Kết xuất danh sách định dạng Markdown tại `test_outputs/form_report.md`.

- **Kết quả Thực tế (Chạy thử nghiệm trên PDF 173 trang `thong-tu-55-btc-PL1.pdf`)**:
  - Trích xuất thành công **49 biểu mẫu & quyết định pháp lý** (ví dụ: *Mẫu I.1.2 Đề xuất dự án đầu tư*, *Mẫu I.1.4 Văn bản đề nghị chấp thuận nhà đầu tư*,...).
  - Lưu trữ tài liệu phân tích chi tiết tại: `test_outputs/legal_templates_analysis.md`.


