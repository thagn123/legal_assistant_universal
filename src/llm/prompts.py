"""
Vietnamese legal system prompts and structured query templates.

All prompts are authored in Vietnamese for optimal performance with
Vietnamese legal content. English field names are used for JSON outputs
to ensure reliable parsing across different LLM temperature settings.
"""

from __future__ import annotations

# ── System prompt ────────────────────────────────────────────────────────────

LEGAL_SYSTEM_PROMPT = """\
Bạn là trợ lý pháp lý AI chuyên về pháp luật Việt Nam, được tích hợp với \
cơ sở dữ liệu văn bản pháp luật và hệ thống gợi ý thông minh.

NGUYÊN TẮC:
• Chỉ căn cứ vào pháp luật Việt Nam hiện hành.
• Luôn trích dẫn nguồn cụ thể (tên luật, số điều, năm ban hành).
• Phân biệt rõ: thông tin từ văn bản được cung cấp vs. kiến thức chung.
• Cảnh báo kịp thời về thời hiệu, rủi ro quan trọng.
• Khuyến nghị tham khảo luật sư cho vụ việc phức tạp.
• Không bịa đặt điều luật hoặc phán quyết không có trong dữ liệu.

ĐỊNH DẠNG: Cấu trúc rõ ràng với tiêu đề in đậm, danh sách có đánh số/dấu đầu dòng.\
"""

# ── Situation analysis ───────────────────────────────────────────────────────

SITUATION_ANALYSIS_PROMPT = """\
Dựa trên thông tin pháp lý đã thu thập, hãy cung cấp phân tích toàn diện.

TÌNH HUỐNG: {situation}
VAI TRÒ NGƯỜI DÙNG: {role_label}
LĨNH VỰC PHÁP LÝ: {law_type}

CÁC ĐIỀU LUẬT TÌM ĐƯỢC TỪ CƠ SỞ DỮ LIỆU:
{law_context}

CÁC VỤ VIỆC TƯƠNG TỰ:
{case_context}

Hãy phân tích theo cấu trúc sau (bắt buộc):

## 1. TÓM TẮT TÌNH HUỐNG
[2-3 câu tóm tắt vấn đề pháp lý cốt lõi]

## 2. ĐÁNH GIÁ VỊ THẾ PHÁP LÝ
**Mức độ:** Mạnh / Trung bình / Yếu
**Điểm mạnh:**
- [liệt kê]
**Điểm yếu:**
- [liệt kê]
**Lý do:** [giải thích 2-3 câu dựa trên điều luật cụ thể]

## 3. CÁC ĐIỀU LUẬT ÁP DỤNG
[Chỉ trích dẫn từ tài liệu được cung cấp ở trên]
- **[Tên luật, Điều X]:** [tóm tắt nội dung áp dụng cho tình huống này]

## 4. HÀNH ĐỘNG ĐỀ XUẤT (theo thứ tự ưu tiên)
1. [Hành động ngay lập tức — cụ thể, có thể thực hiện được]
2. [Hành động tiếp theo trong 7-30 ngày]
3. [Hành động dài hạn / chuẩn bị kiện tụng]

## 5. CẢNH BÁO RỦI RO
- ⏰ **Thời hiệu:** [thời hạn quan trọng cần chú ý]
- ⚠️ **Rủi ro pháp lý:** [liệt kê rủi ro cụ thể]
- 📁 **Bằng chứng còn thiếu:** [tài liệu cần bổ sung]

## 6. KẾT LUẬN
[1-2 câu khuyến nghị tổng thể — rõ ràng, thực tế]\
"""

# ── Entity extraction ─────────────────────────────────────────────────────────

ENTITY_EXTRACTION_PROMPT = """\
Trích xuất các thực thể pháp lý từ tình huống sau.
Trả về JSON hợp lệ, không có markdown code block.

Tình huống: "{situation}"

Cấu trúc JSON yêu cầu:
{{
  "parties": ["tên các bên liên quan"],
  "legal_issues": ["các vấn đề pháp lý chính"],
  "dispute_type": "loại tranh chấp (đất đai/hợp đồng/lao động/doanh nghiệp/hình sự/dân sự)",
  "law_domain": "lĩnh vực pháp lý slug (dat_dai/hop_dong/lao_dong/doanh_nghiep/hinh_su/dan_su)",
  "key_facts": ["các sự kiện pháp lý quan trọng"],
  "time_sensitive": true/false,
  "urgency": "cao/trung_binh/thap"
}}\
"""

# ── Contract analysis ─────────────────────────────────────────────────────────

CONTRACT_ANALYSIS_PROMPT = """\
Phân tích hợp đồng sau theo pháp luật Việt Nam. Xác định điều khoản rủi ro và đề xuất cải thiện.

LOẠI HỢP ĐỒNG: {contract_type}

NỘI DUNG HỢP ĐỒNG:
{contract_text}

CÁC RỦI RO TƯƠNG TỰ TỪ CSDL:
{risk_context}

Phân tích theo cấu trúc sau:

## 1. TỔNG QUAN HỢP ĐỒNG
**Loại:** [xác định loại hợp đồng]
**Các bên:** [bên A và bên B]
**Phạm vi:** [nội dung chính của hợp đồng]
**Giá trị:** [nếu có]

## 2. CÁC ĐIỀU KHOẢN CHÍNH
[Liệt kê và phân loại các điều khoản quan trọng]

## 3. ĐIỀU KHOẢN RỦI RO CAO ⚠️
Mỗi mục theo định dạng:
**[Điều X — Tên điều khoản]**
- Rủi ro: [mô tả rủi ro cụ thể]
- Cơ sở pháp lý: [điều luật vi phạm hoặc chưa tuân thủ]
- Đề xuất: [sửa đổi cụ thể]

## 4. ĐIỀU KHOẢN CÒN THIẾU
[Các điều khoản quan trọng thường có trong loại hợp đồng này nhưng đang thiếu]

## 5. ĐIỂM TUÂN THỦ PHÁP LUẬT: [0-100]/100
**Lý do:** [giải thích điểm số]

## 6. KHUYẾN NGHỊ HÀNH ĐỘNG
1. [Việc cần làm NGAY trước khi ký]
2. [Điều khoản cần đàm phán lại]
3. [Tài liệu bổ sung cần có]\
"""

# ── Risk assessment ───────────────────────────────────────────────────────────

RISK_ASSESSMENT_PROMPT = """\
Đánh giá rủi ro pháp lý cho tình huống sau và trả về JSON hợp lệ (không có markdown).

Tình huống: {situation}
Người dùng: {user_role}
Lĩnh vực: {law_type}

Dữ liệu rủi ro từ hệ thống:
{risk_context}

Trả về JSON:
{{
  "overall_risk_level": "cao|trung_binh|thap",
  "risk_score": 0.0-1.0,
  "risks": [
    {{
      "name": "tên rủi ro",
      "severity": "cao|trung_binh|thap",
      "description": "mô tả",
      "probability": 0.0-1.0,
      "mitigation": ["biện pháp 1", "biện pháp 2"]
    }}
  ],
  "immediate_actions": ["hành động 1", "hành động 2"],
  "strengths": ["điểm mạnh 1"],
  "weaknesses": ["điểm yếu 1"]
}}\
"""

# ── Similar case summary ──────────────────────────────────────────────────────

CASE_COMPARISON_PROMPT = """\
So sánh tình huống hiện tại với các vụ việc tương tự và rút ra bài học.

TÌNH HUỐNG HIỆN TẠI: {situation}

VỤ VIỆC TƯƠNG TỰ:
{cases_context}

Hãy:
1. Chỉ ra điểm tương đồng và khác biệt quan trọng
2. Kết quả nào có thể xảy ra dựa trên các vụ tương tự
3. Chiến lược nào đã thành công trong các vụ tương tự
4. Cảnh báo nào từ các vụ thất bại\
"""
