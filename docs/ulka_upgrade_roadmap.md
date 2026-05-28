# Kế hoạch & Lộ trình Nâng cấp: Chunker Pháp lý, Xuất Báo cáo & Phân tích Trực quan Dashboard

Tài liệu này vạch ra kế hoạch chi tiết để nâng cấp 3 tính năng cốt lõi tiếp theo cho hệ sinh thái **LexAI / Universal Legal Knowledge Assistant**.

---

## TÍNH NĂNG 2: Nâng cấp Bộ tách chunk văn bản (Structured & Semantic Legal Chunker)

### 1. Đối chiếu & Phân tích logic từ `rag_intern`

Trong thư mục `rag_intern/processing/chunking/legal_chunker.py`, bộ tách `LegalChunker` sử dụng biểu thức chính quy (Regex) để phân đoạn tài liệu thô một cách tuần tự dựa trên cấu trúc phân cấp pháp luật Việt Nam:

```python
ARTICLE_RE = re.compile(r"^(Điều|ĐIỀU|Article)\s+\d+")
CHAPTER_RE = re.compile(r"^(Chương|CHƯƠNG|Chapter)\s+")
SECTION_RE = re.compile(r"^(Mục|MỤC|Section)\s+")
CLAUSE_RE = re.compile(r"^\s*(\d+\.|Khoản\s+\d+)")
```

* **Điểm mạnh:** Giúp nhận diện chuẩn xác các khối thô (Raw Blocks) của văn bản OCR lệch chuẩn khi cấu trúc định dạng cây (Canonical Structurer) không được định vị đúng.
* **Cơ chế ngắt thông minh:** Khi độ dài vượt quá giới hạn tối đa (`max_tokens`), nó sẽ tách theo từng Khoản (`CLAUSE_RE`) thay vì cắt ngang từ ở giữa câu, đồng thời kế thừa tiêu đề chương/mục vào embedding text (`embedding_text`) để tối ưu hóa tìm kiếm ngữ nghĩa.

### 2. Thiết kế triển khai nâng cấp trong LexAI

Chúng ta sẽ cải tiến `src/pipeline/chunker.py` và `src/pipeline/structurer.py`:

* **Cải tiến 1: Tăng cường nhận diện Regex trong Structurer (`structurer.py`):**
  Thêm bộ phân giải thô sử dụng `ARTICLE_RE`, `CHAPTER_RE`, `SECTION_RE` và `CLAUSE_RE` vào giai đoạn dọn dẹp khối thô để đảm bảo 100% các dòng dạng "Điều 1...", "Khoản 2..." được định vị đúng thẻ `parent_structure_id`, loại bỏ hoàn toàn việc phân nhóm sai của OCR thô.
  
* **Cải tiến 2: Kế thừa ngữ cảnh phân cấp đầy đủ (Hierarchy Context Carryover):**
  Trong `src/pipeline/chunker.py`, sửa đổi hàm gộp văn bản của Điều/Khoản để luôn đính kèm chuỗi phân cấp đầy đủ làm header của chunk nội dung.
  
  ```python
  # Ví dụ trong chunker.py:
  structure_path = _build_path(article, document) # ["Chương II", "Mục 1", "Điều 12"]
  path_header = " › ".join(structure_path)
  
  # Nội dung chunk lưu trữ sẽ có định dạng:
  content = f"{path_header}\n\n## {article.label}\n\n{body_text}"
  ```
  *Ý nghĩa:* Khi Vector Search trả về một chunk lẻ, LLM vẫn biết chính xác nội dung này thuộc Điều nào, Chương nào mà không cần truy vấn ngược.

---

## TÍNH NĂNG 3: Xuất Báo cáo Kết quả Phân tích (PDF/Docx Export)

Để người dùng có thể in ấn hoặc lưu trữ các kết quả phân tích chất lượng cao từ trang **Phân tích rủi ro hợp đồng** (`Contract.tsx`) hoặc **Báo cáo chứng cứ còn thiếu** (`EvidenceGap.tsx`), chúng ta sẽ triển khai cơ chế kết xuất báo cáo:

### Cấp độ 1: In trực quan phía Client (CSS Print & html2pdf.js)

1. **Cấu hình CSS Print (`src/index.css`):**
   Định nghĩa các vùng in sạch đẹp, ẩn thanh Sidebar điều hướng, nút bấm, bong bóng nhập chat khi in:
   ```css
   @media print {
     aside, button, select, input, textarea, .no-print {
       display: none !important;
     }
     .print-container {
       width: 100% !important;
       max-width: 100% !important;
       background: white !important;
       color: black !important;
       box-shadow: none !important;
       border: none !important;
       padding: 0 !important;
     }
     body {
       background: white !important;
       color: black !important;
     }
   }
   ```
2. **Nút Export PDF trên UI:**
   Sử dụng thư viện `html2pdf.js` để kết xuất vùng chứa kết quả AI thành PDF chất lượng cao chỉ với một dòng lệnh:
   ```typescript
   import html2pdf from 'html2pdf.js';

   const exportPDF = () => {
     const element = document.getElementById('report-area');
     const opt = {
       margin:       [10, 10, 10, 10],
       filename:     'LexAI_Bao_Cao_Phap_Ly.pdf',
       image:        { type: 'jpeg', quality: 0.98 },
       html2canvas:  { scale: 2 },
       jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
     };
     html2pdf().set(opt).from(element).save();
   };
   ```

---

## TÍNH NĂNG 4: Thống kê & Phân tích Trực quan ở trang Tổng quan (Dashboard)

Chúng ta sẽ nâng cấp trang Tổng quan (`Dashboard.tsx`) thành một giao diện quản trị (Admin/Dashboard) hiện đại, tích hợp thư viện **Recharts** để trực quan hóa dữ liệu RAG và tiến trình pháp lý của người dùng.

### 1. Phân bổ rủi ro Hợp đồng (Risk Distribution Chart)
* **Loại biểu đồ:** Pie Chart (Biểu đồ tròn) hoặc Radar Chart (Mạng nhện).
* **Mô tả:** Thống kê tỷ lệ phần trăm các điều khoản rủi ro quét được từ hợp đồng (Thấp, Trung bình, Cao, Nghiêm trọng).

```typescript
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const riskData = [
  { name: 'Nghiêm trọng', value: 12, color: '#EF4444' }, // đỏ
  { name: 'Cao', value: 25, color: '#F97316' },          // cam
  { name: 'Trung bình', value: 45, color: '#EAB308' },    // vàng
  { name: 'Thấp', value: 18, color: '#10B981' }          // xanh lá
];
```

### 2. Tiến trình xử lý vụ việc (Case Pipeline Timeline)
* **Loại biểu đồ:** Bar Chart dạng ngang (Horizontal Bar Chart).
* **Mô tả:** Trực quan hóa tiến độ các bước của Lộ trình Cá nhân hóa (Journey Steps) đối với các vụ việc mà người dùng đang phân tích.

### 3. Compliance Radar (Liên kết tuân thủ)
* **Loại biểu đồ:** Area Chart / Line Chart.
* **Mô tả:** Theo dõi điểm số tuân thủ pháp luật (Compliance Score) của doanh nghiệp hoặc hợp đồng qua các lần quét hàng tháng, giúp kiểm soát mức độ cải thiện hệ thống kiểm soát nội bộ.

### Các file giao diện cần sửa đổi:
* `src/pages/Dashboard.tsx`
* Cài đặt thư viện: `npm install recharts lucide-react`
