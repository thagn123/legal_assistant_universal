# Demo Inputs & Expected Outputs — LexAI / ULKA

Dùng file này để:
1. Copy-paste input khi quay video
2. Kiểm tra output trước khi quay (verify expected)
3. Dùng làm checklist khi làm manual QA

---

## Demo 1 — Đất đai có sổ đỏ

### Input (copy-paste)
```
Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?
```

**POST** `http://localhost:8001/intelligence/analyze`
```json
{
  "situation": "Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?",
  "user_id": "demo_video"
}
```

### Expected Output

| Field | Expected |
|---|---|
| `detected_domain` | `dat_dai` |
| `legal_position_strength` | Mạnh hoặc Trung bình |

**Must appear** trong `recommended_actions` hoặc `full_assessment`:
- "ranh giới" hoặc "đo đạc"
- "chứng cứ" hoặc "biên bản"
- "hòa giải" (bước cần làm — chưa làm)
- "quyền sử dụng đất" hoặc "Luật Đất đai"

**Must NOT appear** trong `recommended_actions`:
- "thu thập sổ đỏ"
- "xin cấp GCN"
- "làm sổ đỏ"
- "chưa có sổ đỏ"
- "đăng ký cấp"
- "bổ sung sổ đỏ"

**Giải thích khi quay:** "Tôi đã khai báo có sổ đỏ. Evidence status = PRESENT. OutputValidator phải loại bỏ action 'thu thập sổ đỏ'."

---

## Demo 2 — Hòa giải không thành (S-05 Bug Story)

### Input (copy-paste)
```
Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.
```

**POST** `http://localhost:8001/intelligence/analyze`
```json
{
  "situation": "Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.",
  "user_id": "demo_video"
}
```

### Expected Output

| Field | Expected |
|---|---|
| `detected_domain` | `dat_dai` |
| Post-mediation flag | Detected (xem `_is_post_mediation_failed`) |

**Must appear** trong `recommended_actions`:
- "biên bản hòa giải không thành" (giữ biên bản làm bằng chứng)
- "khởi kiện" hoặc "Tòa án nhân dân"
- "hồ sơ khởi kiện" hoặc "cấp huyện"
- "chứng cứ" hoặc "đo đạc"

**Must NOT appear** trong `recommended_actions`:
- "Nộp đơn yêu cầu hòa giải tại UBND"
- "thực hiện hòa giải"
- "yêu cầu hòa giải"
- "nộp đơn hòa giải"

**Must appear** trong `full_assessment` / `key_action`:
- "chuẩn bị hồ sơ khởi kiện" hoặc "Tòa án nhân dân cấp huyện"
- "bạn đã hoàn thành" hoặc "đã hoàn thành bước hòa giải"

**Giải thích khi quay:** "Đây là bug P0 được phát hiện trong manual QA. Phiên bản cũ vẫn gợi ý 'đi hòa giải'. Sau fix S-05, hệ thống nhận ra bước này đã hoàn thành và chuyển sang khởi kiện."

---

## Demo 3 — Ly hôn đơn phương có con nhỏ

### Input (copy-paste)
```
Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng tôi không đồng ý ly hôn. Tôi có thể làm được không?
```

**POST** `http://localhost:8001/intelligence/analyze`
```json
{
  "situation": "Tôi muốn ly hôn đơn phương, có con 2 tuổi, chồng tôi không đồng ý ly hôn. Tôi có thể làm được không?",
  "user_id": "demo_video"
}
```

### Expected Output

| Field | Expected |
|---|---|
| `detected_domain` | `gia_dinh` |
| `legal_position_strength` | Trung bình (có thể ly hôn nhưng phức tạp về nuôi con) |

**Must appear** trong response:
- "ly hôn đơn phương" (được phép)
- "Điều 56" hoặc "Luật Hôn nhân Gia đình"
- "nuôi con" hoặc "36 tháng" hoặc "dưới 3 tuổi"
- Tòa án hoặc thủ tục nộp đơn

**Must NOT appear** trong response:
- "không thể ly hôn"
- "không được ly hôn"
- "không có quyền ly hôn"
- "bị từ chối ly hôn" (trừ trường hợp giải thích rõ hoàn cảnh cụ thể)

**Giải thích khi quay:** "Case nhạy cảm. Manual QA yêu cầu: hệ thống không được nói 'không thể ly hôn'. Luật Hôn nhân Gia đình cho phép ly hôn đơn phương."

---

## Demo 4 — Lao động: Nợ lương

### Input
```
Công ty tôi nợ lương 2 tháng, tôi đã nhắc nhiều lần nhưng không được trả. Tôi cần làm gì?
```

### Expected Output

| Field | Expected |
|---|---|
| `detected_domain` | `lao_dong` |

**Must appear:**
- "lương" + "đòi" hoặc "yêu cầu"
- "Bộ luật Lao động" hoặc "luật lao động"
- Cơ quan giải quyết: "Phòng Lao động" hoặc "Tòa án lao động"

**Must NOT appear:**
- Actions liên quan đến đất đai
- Actions liên quan đến hôn nhân

---

## Demo 5 — No-diacritics (Không dấu)

### Input
```
so do cua toi bi hang xom tranh chap ranh gioi, toi can lam gi
```

### Expected Output

| Field | Expected |
|---|---|
| `detected_domain` | `dat_dai` (không phải `general` hoặc `english`) |

**Must appear:**
- Actions liên quan đất đai
- Response bằng tiếng Việt (không phải English)

**Giải thích khi quay:** "Hệ thống nhận dạng tiếng Việt không dấu qua `_VI_INDICATORS_NODIAC`. Q26 trong benchmark: dat_dai ✅."

---

## Demo 6 — Non-legal (Graceful redirect)

### Input
```
Hôm nay thời tiết đẹp ở Hà Nội, đi đâu ăn?
```

### Expected Output

Hệ thống hiện tại trả về domain `hop_dong` cho query này (Q28 known issue). Manual QA S-15 dùng query khác: "Thời tiết Hà Nội hôm nay thế nào?" và kiểm tra xem có hallucination pháp lý không.

**Must NOT appear:**
- Tư vấn pháp lý về hợp đồng liên quan đến ăn uống
- Bất kỳ citation pháp lý nào

**Giải thích:** "Non-legal domain guard là roadmap — tương lai detect zero-score query → trả domain=general."

---

## API Test — Verify Directly

Nếu muốn verify bằng curl hoặc Postman:

```bash
# Demo 1 — verify no land cert suggestion
curl -X POST http://localhost:8001/intelligence/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-ID: demo_video" \
  -d '{"situation": "Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi, tôi cần làm gì?", "user_id": "demo_video"}' \
  | python -m json.tool | grep -A 20 '"recommended_actions"'
```

```bash
# Demo 2 — verify no mediation re-suggestion
curl -X POST http://localhost:8001/intelligence/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-ID: demo_video" \
  -d '{"situation": "Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.", "user_id": "demo_video"}' \
  | python -m json.tool | grep -A 20 '"recommended_actions"'
```

Kết quả Demo 2 phải có "biên bản hòa giải không thành" và **không có** "Nộp đơn yêu cầu hòa giải tại UBND".
