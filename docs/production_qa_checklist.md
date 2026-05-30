# Production QA Checklist — LexAI / ULKA

> **Scope**: End-to-end manual + automated QA trước khi deploy beta.
> **Baseline**: P0 fixed, 297/297 tests pass, threshold configurable via env.
> **Tester role**: simulate người dùng cuối — không nhìn code, chỉ nhìn UI + response.

---

## 1. Manual QA Scenarios

### Ký hiệu cột

| Ký hiệu | Nghĩa |
|---|---|
| ✅ MUST | Phải có — fail nếu thiếu |
| ❌ NEVER | Không được xuất hiện — fail ngay nếu có |
| ⚠️ WARN | Cảnh báo nếu thiếu, không fail cứng |

---

### S-01 — Đất đai có sổ đỏ

**Input (paste vào Analyze):**
```
Tôi có sổ đỏ đứng tên mình nhưng hàng xóm đang lấn chiếm ranh giới đất,
xây tường lấn vào phần đất của tôi khoảng 0.5m. Tôi phải làm gì?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dat_dai` |
| Evidence status | STRONG (sổ đỏ được xác nhận) |
| ✅ MUST appear | hòa giải, UBND, đo đạc địa chính, biên bản |
| ❌ NEVER appear | "bạn chưa có sổ đỏ", "cần làm sổ đỏ trước", "không có căn cứ pháp lý" |
| ❌ NEVER appear | "chưa rõ bạn có giấy tờ không", contradiction về giấy tờ |
| Actions ✅ | Hòa giải UBND → Tòa án nhân dân huyện nếu không thành |
| Actions ❌ | "cần mua bảo hiểm", "thuê luật sư ngay lập tức" (không cần bước đầu) |
| Similar cases ✅ | Tranh chấp ranh giới đất, lấn chiếm đất, tường rào |
| Similar cases ❌ | Vụ việc lao động, ly hôn |
| **Pass criteria** | Domain=dat_dai, evidence nhắc đến sổ đỏ như tài sản hợp lệ, không có lời khuyên contradicting với việc đã có sổ đỏ |

---

### S-02 — Đất đai chưa có sổ đỏ

**Input:**
```
Gia đình tôi đang ở trên mảnh đất 20 năm nhưng chưa làm được sổ đỏ.
Hàng xóm nói mảnh đất đó là của họ và đòi lấy lại. Tôi phải làm gì?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dat_dai` |
| Evidence status | WEAK — chỉ có sử dụng lâu dài, không có giấy tờ |
| ✅ MUST appear | xin cấp GCNQSDĐ, thời hiệu, văn phòng đăng ký đất đai, hòa giải |
| ❌ NEVER appear | "bạn có sổ đỏ", "khởi kiện ngay" (thiếu điều kiện), "chắc chắn thắng kiện" |
| ❌ NEVER appear | Bỏ qua bước xin cấp giấy tờ và nhảy thẳng sang tòa án |
| Actions ✅ | Thu thập chứng cứ sử dụng đất, xin cấp GCN, hòa giải UBND |
| Similar cases ✅ | Tranh chấp đất không có giấy tờ, công nhận quyền sử dụng đất |
| **Pass criteria** | Response nhận ra "chưa có sổ đỏ" và đưa ra lộ trình phù hợp thay vì giả định đã có giấy tờ |

---

### S-03 — GCN QSDĐ / Thu hồi đất

**Input:**
```
Tôi có Giấy chứng nhận quyền sử dụng đất hợp lệ nhưng UBND huyện ra quyết định
thu hồi không báo trước và không bồi thường thỏa đáng. Tôi có thể làm gì?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dat_dai` + `hanh_chinh` (cross-domain) |
| Evidence status | STRONG (GCN hợp lệ) |
| ✅ MUST appear | khiếu nại hành chính, Luật Đất đai 2013/2024, quyết định thu hồi, bồi thường |
| ❌ NEVER appear | "bạn không có giấy tờ gì", "UBND có quyền thu hồi bất kỳ lúc nào vô điều kiện" |
| Actions ✅ | Khiếu nại lần 1 → UBND tỉnh → Tòa Hành chính |
| Similar cases ✅ | Thu hồi đất, khiếu nại quyết định hành chính, bồi thường không thỏa đáng |
| **Pass criteria** | Nhận dạng cross-domain (đất đai + hành chính), không bỏ qua con đường khiếu nại |

---

### S-04 — Bản photo sổ đỏ, mất bản gốc

**Input:**
```
Tôi chỉ có bản photo sổ đỏ, bản gốc bị mất không tìm thấy.
Hàng xóm đang tranh chấp mảnh đất với tôi. Bản photo có giá trị pháp lý không?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dat_dai` |
| Evidence status | PARTIAL — photo không thay thế bản gốc |
| ✅ MUST appear | xin cấp lại bản gốc, Văn phòng đăng ký đất đai, thủ tục cấp lại |
| ❌ NEVER appear | "bản photo có giá trị pháp lý đầy đủ", "bạn có đầy đủ giấy tờ" |
| ❌ NEVER appear | Bỏ qua bước cấp lại và đề xuất khởi kiện ngay với bản photo |
| Actions ✅ | Nộp đơn xin cấp lại GCN → thu thập thêm chứng cứ phụ (hóa đơn điện, nộp thuế…) |
| **Pass criteria** | Response phân biệt rõ bản photo ≠ bản gốc, và hướng dẫn cấp lại trước khi kiện |

---

### S-05 — Hòa giải không thành

**Input:**
```
Tôi đã hòa giải tranh chấp đất tại UBND xã nhưng không thành công.
Biên bản hòa giải không thành đã được lập. Bước tiếp theo tôi phải làm gì?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dat_dai` |
| Evidence status | hòa giải không thành = điều kiện để khởi kiện |
| ✅ MUST appear | Tòa án nhân dân, nộp đơn khởi kiện, biên bản hòa giải không thành, án phí |
| ❌ NEVER appear | "nên hòa giải trước tiên" (đã làm rồi), "tiến hành hòa giải tại UBND" |
| ❌ NEVER appear | Đề xuất các bước trước hòa giải (mâu thuẫn với context đã có) |
| Actions ✅ | Chuẩn bị hồ sơ khởi kiện, nộp tòa huyện/tỉnh |
| **Pass criteria** | KHÔNG đề xuất "hòa giải là bước đầu tiên" — P0 contradiction prevention. Response phải nhận ra "hòa giải không thành" và chuyển sang escalation path. |

---

### S-06 — Bên thuê nhà

**Input:**
```
Tôi đang thuê nhà, đã đóng tiền thuê đúng hạn 6 tháng nay.
Chủ nhà đột ngột gọi điện đuổi tôi trong vòng 3 ngày mà không có lý do.
Hợp đồng còn 4 tháng nữa mới hết hạn.
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `hop_dong` (dan_su) |
| Evidence status | STRONG (hợp đồng còn hiệu lực, đóng tiền đúng hạn) |
| ✅ MUST appear | thông báo trước, vi phạm hợp đồng, bồi thường, tiền đặt cọc hoàn lại |
| ❌ NEVER appear | "chủ nhà có quyền đuổi bất cứ lúc nào", "bạn phải dọn đi" |
| Actions ✅ | Yêu cầu bồi thường, tố cáo vi phạm hợp đồng, hòa giải/khởi kiện nếu cần |
| Similar cases ✅ | Tranh chấp hợp đồng thuê nhà, đơn phương chấm dứt |
| **Pass criteria** | Xác định rõ quyền của bên thuê, không để chủ nhà có "full power" |

---

### S-07 — Bên cho thuê

**Input:**
```
Tôi cho thuê nhà, người thuê không trả tiền 3 tháng liên tiếp và làm hỏng
nhiều đồ đạc trong nhà. Tôi muốn đuổi họ ra và đòi bồi thường thiệt hại.
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `hop_dong` |
| Evidence status | cần hợp đồng + chứng cứ thiệt hại |
| ✅ MUST appear | đơn phương chấm dứt hợp đồng, thông báo, bồi thường thiệt hại, biên bản hiện trạng |
| ❌ NEVER appear | "không làm gì được", "phải chờ hợp đồng hết hạn" |
| Actions ✅ | Lập biên bản, gửi thông báo chấm dứt, khởi kiện đòi nợ tiền thuê + thiệt hại |
| **Pass criteria** | Hướng dẫn cả 2 hướng (chấm dứt hợp đồng + đòi bồi thường) song song |

---

### S-08 — Nợ lương

**Input:**
```
Công ty tôi đang làm nợ lương 2 tháng liên tiếp, ban giám đốc không
trả lời và nói "chờ thêm". Tôi có hợp đồng lao động. Tôi phải làm gì?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `lao_dong` |
| Evidence status | STRONG (hợp đồng lao động có) |
| ✅ MUST appear | Phòng LĐTBXH, thanh tra lao động, khiếu nại, lãi suất chậm trả lương |
| ❌ NEVER appear | "không có quyền đòi lương", "đây không phải vi phạm pháp luật" |
| Actions ✅ | Gửi yêu cầu bằng văn bản → khiếu nại LĐTBXH → khởi kiện Tòa lao động |
| Similar cases ✅ | Chậm trả lương, vi phạm hợp đồng lao động, bồi thường |
| **Pass criteria** | Nhắc đến quyền đòi lãi suất chậm trả (Điều 96 BLLĐ 2019) |

---

### S-09 — Sa thải trái pháp luật

**Input:**
```
Tôi bị sa thải đột ngột, không có thông báo trước 45 ngày, không được
nhận trợ cấp thôi việc, công ty nói tôi "không phù hợp văn hóa công ty".
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `lao_dong` |
| Evidence status | STRONG nếu có hợp đồng; PARTIAL nếu chỉ miệng |
| ✅ MUST appear | sa thải trái pháp luật, 45 ngày, trợ cấp thôi việc, bồi thường |
| ❌ NEVER appear | "sa thải vì văn hóa công ty là hợp pháp", "bạn không được bồi thường" |
| ❌ NEVER appear | Bỏ qua lý do sa thải không hợp lệ |
| Actions ✅ | Yêu cầu quyết định sa thải bằng văn bản, khiếu nại, Tòa lao động |
| Similar cases ✅ | Sa thải trái pháp luật, tranh chấp hợp đồng lao động |
| **Pass criteria** | "không phù hợp văn hóa" KHÔNG được liệt kê là lý do sa thải hợp pháp |

---

### S-10 — Ly hôn có con nhỏ

**Input:**
```
Tôi muốn ly hôn nhưng chồng không chịu ký đơn. Chúng tôi có con 2 tuổi.
Tôi muốn nuôi con. Tôi có thể làm được không?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `gia_dinh` |
| Evidence status | con dưới 36 tháng → ưu tiên mẹ nuôi (Luật HNGĐ Điều 81) |
| ✅ MUST appear | ly hôn đơn phương, Tòa án, con dưới 36 tháng, quyền nuôi con |
| ❌ NEVER appear | "không thể ly hôn nếu chồng không đồng ý" (sai — có thể ly hôn đơn phương) |
| ❌ NEVER appear | "chồng sẽ được nuôi con" (vi phạm quy định Điều 81 HNGĐ) |
| Actions ✅ | Nộp đơn ly hôn đơn phương → Tòa án → chứng minh điều kiện nuôi con |
| Similar cases ✅ | Ly hôn đơn phương, tranh chấp nuôi con, cấp dưỡng |
| **Pass criteria** | KHÔNG nói "không thể ly hôn" — P0 prevention. Phải nhắc rõ quyền đơn phương. |

---

### S-11 — Hợp đồng đã ký, bên bán vi phạm

**Input:**
```
Tôi đã ký hợp đồng mua căn hộ, đã thanh toán 80% giá trị.
Bên bán không giao nhà đúng hạn, đã trễ 6 tháng và không có lý do rõ ràng.
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `hop_dong` (dan_su) |
| Evidence status | STRONG (hợp đồng đã ký, đã thanh toán) |
| ✅ MUST appear | phạt vi phạm, bồi thường thiệt hại, yêu cầu tiếp tục thực hiện hoặc hủy HĐ |
| ❌ NEVER appear | "bạn chưa có hợp đồng", "không thể đòi gì vì chưa nhận nhà" |
| Actions ✅ | Gửi văn bản yêu cầu → thương lượng phạt chậm → khởi kiện |
| Similar cases ✅ | Vi phạm hợp đồng mua bán bất động sản, giao hàng trễ hạn |
| **Pass criteria** | Đề cập rõ điều khoản phạt vi phạm (thường 8%/năm theo BLDS 2015) |

---

### S-12 — Hợp đồng chưa ký, đã đặt cọc

**Input:**
```
Tôi đã đặt cọc 50 triệu để mua nhà nhưng chưa ký hợp đồng chính thức.
Bên bán giờ muốn bán cho người khác giá cao hơn và muốn trả lại cọc.
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `dan_su` (hop_dong) |
| Evidence status | PARTIAL — đặt cọc có, hợp đồng chưa có |
| ✅ MUST appear | phạt cọc (×2), Điều 328 BLDS 2015, đặt cọc |
| ❌ NEVER appear | "bạn có hợp đồng đầy đủ", "không được bồi thường gì" |
| Actions ✅ | Yêu cầu bên bán bồi thường phạt cọc × 2 = 100 triệu, hoặc tiếp tục ký HĐ |
| **Pass criteria** | Nêu đúng cơ chế phạt cọc (bên nhận cọc vi phạm → trả lại + thêm một khoản bằng cọc) |

---

### S-13 — Query không dấu / sai chính tả

**Input:**
```
toi bi sai thai khong co ly do chinh dang cong ty khong tra tro cap
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `lao_dong` (phải detect được từ "sai thai" = sa thải) |
| Evidence status | varies |
| ✅ MUST appear | response có nội dung, domain được nhận dạng |
| ❌ NEVER appear | response trống, domain=general khi rõ là lao động, error 500 |
| **Pass criteria** | Domain=lao_dong hoặc response đề cập lao động/sa thải; không crash; không trả về "tôi không hiểu câu hỏi" với trường hợp rõ ràng |

---

### S-14 — Query đa domain

**Input:**
```
Tôi vừa bị sa thải bất hợp pháp vừa đang có tranh chấp đất đai với anh họ.
Hai vụ này có liên quan gì không và tôi nên ưu tiên giải quyết cái nào trước?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `lao_dong` + `dat_dai` (multi-domain) |
| Evidence status | mixed |
| ✅ MUST appear | cả hai vấn đề được đề cập, gợi ý ưu tiên |
| ❌ NEVER appear | chỉ trả lời một domain và bỏ qua domain kia hoàn toàn |
| Actions ✅ | Tách hai vụ riêng biệt, ưu tiên theo thời hiệu |
| **Pass criteria** | Response đề cập cả sa thải lẫn đất đai; không ignore một trong hai |

---

### S-15 — Query không liên quan pháp luật

**Input:**
```
Hôm nay thời tiết Hà Nội như thế nào? Tôi nên mặc gì đi làm?
```

| Tiêu chí | Giá trị |
|---|---|
| Expected domain | `general` / không phát hiện được |
| ✅ MUST appear | thông báo lịch sự rằng câu hỏi ngoài phạm vi pháp lý |
| ❌ NEVER appear | bịa đặt tư vấn pháp lý, hallucinate luật thời tiết, crash 500 |
| ❌ NEVER appear | Trả về JSON lỗi thô ra UI |
| **Pass criteria** | Graceful redirect, không có legal advice bịa, không crash |

---

## 2. API Smoke Tests

> Chạy bằng `curl` hoặc Postman. Backend tại `http://localhost:8001`.
> Header mặc định: `X-User-ID: qa_smoke_test`.

---

### A. POST `/intelligence/analyze`

```bash
curl -X POST http://localhost:8001/intelligence/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-ID: qa_smoke_test" \
  -d '{
    "query": "Tôi bị sa thải không có lý do, không nhận trợ cấp",
    "session_id": "smoke_test_001"
  }'
```

| Check | Expected |
|---|---|
| HTTP status | 200 |
| `detected_domain` | `lao_dong` |
| `full_assessment` present | true, length > 100 chars |
| `full_assessment` contains | không chứa "chắc chắn thắng", không chứa template placeholder |
| `recommendations` | list, length >= 1 |
| `contradictions` | không có contradiction lao_dong vs đất đai |
| `evidence_status` | field exists |
| Response time | < 10s (LLM) / < 2s (deterministic fallback) |

---

### B. POST `/analysis/evidence-gap`

```bash
curl -X POST http://localhost:8001/analysis/evidence-gap \
  -H "Content-Type: application/json" \
  -H "X-User-ID: qa_smoke_test" \
  -d '{
    "situation": "Tôi bị sa thải, có hợp đồng lao động",
    "domain": "lao_dong",
    "existing_evidence": ["hop_dong_lao_dong"]
  }'
```

| Check | Expected |
|---|---|
| HTTP status | 200 |
| `gaps` | list, không rỗng khi situation có nội dung |
| `gap_severity` | có giá trị hợp lệ |
| Không có field `null` thô trong response | — |
| Không có evidence giả (gap không relate đến situation) | — |

---

### C. GET `/retrieval/laws`  → POST `/retrieval/laws`

```bash
curl -X POST http://localhost:8001/retrieval/laws \
  -H "Content-Type: application/json" \
  -H "X-User-ID: qa_smoke_test" \
  -d '{"query": "Quyền sử dụng đất khi chưa có sổ đỏ"}'
```

| Check | Expected |
|---|---|
| HTTP status | 200 |
| `results` | list |
| Tất cả results có `vector_score` | Nếu MongoDB có data: tất cả >= 0.55 (LAW_VECTOR_SCORE_THRESHOLD) |
| `search_mode` | `vector`, `keyword`, hoặc `demo_fallback` |
| `total` | match len(results) |
| Demo fallback khi MongoDB trống | `search_mode=demo_fallback`, results có nội dung hữu ích |

---

### D. POST `/retrieval/similar-cases`

```bash
curl -X POST http://localhost:8001/retrieval/similar-cases \
  -H "Content-Type: application/json" \
  -H "X-User-ID: qa_smoke_test" \
  -d '{
    "situation": "Bị sa thải trái pháp luật không có thông báo trước",
    "domain_hint": "lao_dong",
    "include_community": false,
    "persist_anonymized": false
  }'
```

| Check | Expected |
|---|---|
| HTTP status | 200 |
| `official_cases` | list |
| Tất cả `official_cases` có `vector_score` | >= 0.55 nếu từ MongoDB thật |
| Demo cases có `is_demo=true` | ✅ mandatory |
| Demo cases KHÔNG có `is_demo=false` | ✅ mandatory |
| `fallback_used` | boolean, có mặt trong response |
| Top case domain | `lao_dong` khi domain_hint=lao_dong (trừ khi không có case lao_dong nào) |
| Không có cross-domain score < 0.55 lọt vào | Validate từng item |

---

### E. POST `/recommendations/next-best-actions`

```bash
curl -X POST http://localhost:8001/recommendations/next-best-actions \
  -H "Content-Type: application/json" \
  -H "X-User-ID: qa_smoke_test" \
  -d '{
    "situation": "Bị sa thải, nợ lương 2 tháng",
    "domain": "lao_dong",
    "session_id": "smoke_test_001"
  }'
```

| Check | Expected |
|---|---|
| HTTP status | 200 |
| `actions` | list, length 1-4 |
| Mỗi action có `title`, `description`, `priority` | ✅ |
| Actions không mâu thuẫn nhau | "hòa giải" và "khởi kiện ngay" không xuất hiện cùng nhau ở cùng priority |
| Actions phù hợp với domain `lao_dong` | Không xuất hiện "làm sổ đỏ" |

---

## 3. Frontend Smoke Tests

> Mở `http://localhost:3000`. Dùng browser devtools (F12) để monitor network + console errors.

### F-01 — Analyze Page

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Load `/` hoặc `/analyze` | Trang hiện đúng, không có console error |
| 2 | Nhập S-09 (sa thải) vào chatbox | Input nhận ký tự không lag |
| 3 | Submit | Loading spinner xuất hiện |
| 4 | Chờ response | Response hiển thị trong vòng 15s |
| 5 | Kiểm tra domain badge | Hiển thị "Lao động" |
| 6 | Scroll qua toàn bộ response | Không có placeholder `{{...}}` hay `[object Object]` |
| 7 | Nhập S-05 (hòa giải không thành) | Response KHÔNG đề xuất "hòa giải trước" |
| 8 | Nhập S-15 (query phi pháp lý) | Graceful response, không crash |

---

### F-02 — Dashboard

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Load `/dashboard` | Widget load trong < 3s |
| 2 | NBA chips hiển thị | 1-4 action chips xuất hiện |
| 3 | Click NBA chip | Navigate sang đúng trang với context |
| 4 | Behavior chart | Chart render, không blank |
| 5 | Refresh trang | Không mất dữ liệu, không flicker |

---

### F-03 — Evidence Gap Page

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Load `/evidence-gap` | Trang load, không 404 |
| 2 | Nhập situation S-04 (photo sổ đỏ) | Submit thành công |
| 3 | Kết quả hiện | Gaps hiển thị dạng list, không JSON thô |
| 4 | Save button click | Toast "Đã lưu" xuất hiện trong < 2s |
| 5 | Check `/history` | Saved item xuất hiện |

---

### F-04 — Similar Cases Component

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Navigate đến trang Similar Cases | Trang load |
| 2 | Submit S-06 (thuê nhà) | Cases hiển thị |
| 3 | Demo case badge | Cases từ demo có badge "Ví dụ tham khảo" |
| 4 | Real cases | Không có "Ví dụ tham khảo" badge |
| 5 | Domain filter hiện | Top case domain khớp với query domain |
| 6 | Nhập query phi lao động, domain=dat_dai | Không có lao_dong case dẫn đầu |

---

### F-05 — Document Search / Law Search

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Load `/law-search` | Trang load |
| 2 | Search "Điều 81 Luật Hôn nhân" | Kết quả trả về |
| 3 | Kết quả có law_reference | Không blank |
| 4 | Search query không liên quan | Fallback message rõ ràng |

---

### F-06 — Loading / Empty / Error States

| Scenario | Expected |
|---|---|
| Backend down (kill backend) | UI hiển thị "Không thể kết nối" — không white screen |
| Query trả về 0 kết quả | Empty state có message hướng dẫn |
| Loading > 5s | Spinner vẫn visible, không bị stuck |
| Network slow (throttle 3G) | No infinite loading, timeout hiển thị |
| Console errors | Zero errors trong happy path |

---

### F-07 — Session / History Persistence

| Bước | Hành động | Expected |
|---|---|---|
| 1 | Phân tích vụ S-09 (sa thải) | Response xuất hiện |
| 2 | Refresh page (F5) | Conversation history còn đó (localStorage) |
| 3 | Đóng tab, mở lại | History còn đó |
| 4 | Click "Lưu" | Toast + item xuất hiện trong `/history` |
| 5 | Vào `/history` | Items hiển thị đúng loại, có preview |
| 6 | Download JSON | File download được, JSON hợp lệ |
| 7 | Delete item | Item biến mất khỏi list |

---

## 4. Retrieval Benchmark Plan

> **Mục tiêu đo**: xác minh retrieval quality khi MongoDB Atlas có data thật.
> **Phương pháp**: chạy mỗi query, ghi top-1 domain, top-1 score, có fallback không.
> **Cột đo**: Domain | Top-1 Score | Top-3 Relevant (Y/N) | Fallback? | Notes

### 30 Benchmark Queries

| # | Query | Expected Domain | Acceptance |
|---|---|---|---|
| Q01 | "Hàng xóm lấn chiếm ranh giới đất của tôi" | dat_dai | top-1 dat_dai |
| Q02 | "Chưa có sổ đỏ, ở 15 năm, bị đòi đất" | dat_dai | top-1 dat_dai |
| Q03 | "Thu hồi đất không bồi thường thỏa đáng" | dat_dai + hanh_chinh | cross-domain OK |
| Q04 | "Sổ đỏ bị mất, thủ tục cấp lại" | dat_dai | top-1 dat_dai |
| Q05 | "Mua đất chưa sang tên, bên bán không chịu" | dat_dai + hop_dong | OK |
| Q06 | "Sa thải không báo trước 45 ngày" | lao_dong | top-1 lao_dong |
| Q07 | "Công ty nợ lương 3 tháng không trả" | lao_dong | top-1 lao_dong |
| Q08 | "Tai nạn lao động, công ty không đền bù" | lao_dong | top-1 lao_dong |
| Q09 | "BHXH bị trừ nhưng không đóng" | lao_dong | top-1 lao_dong |
| Q10 | "Hợp đồng lao động không có thời hạn bị chấm dứt" | lao_dong | top-1 lao_dong |
| Q11 | "Ly hôn đơn phương vì chồng bạo lực gia đình" | gia_dinh | top-1 gia_dinh |
| Q12 | "Tranh chấp nuôi con sau ly hôn" | gia_dinh | top-1 gia_dinh |
| Q13 | "Con dưới 36 tháng tuổi, ai được nuôi" | gia_dinh | top-1 gia_dinh, Điều 81 |
| Q14 | "Thừa kế nhà đất khi không có di chúc" | dan_su | top-1 dan_su |
| Q15 | "Chia tài sản chung khi ly hôn" | gia_dinh + dan_su | OK |
| Q16 | "Hợp đồng mua bán không công chứng có hiệu lực không" | hop_dong | top-1 hop_dong |
| Q17 | "Đặt cọc mua nhà bị mất khi bên bán nuốt lời" | dan_su + hop_dong | phạt cọc ×2 |
| Q18 | "Thuê nhà bị đuổi trước hạn không lý do" | hop_dong | top-1 hop_dong |
| Q19 | "Hợp đồng thương mại vi phạm điều khoản thanh toán" | hop_dong + doanh_nghiep | OK |
| Q20 | "Phá sản doanh nghiệp, quyền của người lao động" | doanh_nghiep + lao_dong | cross-domain OK |
| Q21 | "Khiếu nại quyết định hành chính UBND" | hanh_chinh | top-1 hanh_chinh |
| Q22 | "Tố cáo cán bộ nhà nước tham nhũng" | hanh_chinh + hinh_su | OK |
| Q23 | "Bị lừa đảo chiếm đoạt tài sản" | hinh_su | top-1 hinh_su |
| Q24 | "Tội trộm cắp, mức phạt tù bao nhiêu" | hinh_su | top-1 hinh_su |
| Q25 | "Hòa giải đất đai không thành bước tiếp theo" | dat_dai | KHÔNG đề xuất hòa giải lần nữa |
| Q26 | "toi bi sai thai khong co hop dong" (không dấu) | lao_dong | detect được, không crash |
| Q27 | "I was wrongfully terminated from my job in Vietnam" | lao_dong | cross-language, top-1 lao_dong |
| Q28 | "Land dispute neighbor encroachment boundary" | dat_dai | cross-language OK |
| Q29 | "Vừa bị sa thải vừa bị đòi đất, ưu tiên gì" | multi-domain | cả 2 đề cập |
| Q30 | "Hôm nay trời có mưa không" | general | graceful redirect |

### Đo lường

| Metric | Formula | Target |
|---|---|---|
| Top-1 Relevance | (Q có top-1 đúng domain) / 28 query có domain rõ | ≥ 85% |
| Top-3 Relevance | ≥ 1 trong 3 kết quả đúng domain | ≥ 92% |
| Avg top-1 score | Trung bình vector_score của kết quả #1 (bỏ demo) | ≥ 0.60 |
| Score < 0.55 rate | Tỉ lệ real results có score < 0.55 lọt vào response | 0% (threshold enforced) |
| Fallback/demo rate | Số query kích hoạt demo_fallback / 30 | ≤ 30% khi có data |
| Cross-domain error | lao_dong case dẫn đầu dat_dai query | 0% |
| Empty response rate | Response có `total=0` và không có fallback | 0% |
| Crash/500 rate | HTTP 5xx | 0% |

### Cách chạy

```bash
# Chạy benchmark script (tạo khi cần)
python scripts/run_retrieval_benchmark.py \
  --queries docs/production_qa_checklist.md \
  --output reports/retrieval_benchmark_$(date +%Y%m%d).json
```

Hoặc chạy thủ công từng query trong Postman, ghi vào spreadsheet:

| Query # | Top-1 domain | Top-1 score | Top-3 relevant | Fallback | Notes |
|---|---|---|---|---|---|
| Q01 | | | | | |
| ... | | | | | |

---

## 5. Release Gate

### 5.1 Hard Gates — Fail = No Deploy

| Gate | Điều kiện fail | Ghi chú |
|---|---|---|
| P0 contradiction | BẤT KỲ scenario nào có contradiction (S-05, S-10) fail | Zero tolerance |
| Hallucination | Response khẳng định sai luật (sa thải hợp pháp khi không phải) | Zero tolerance |
| HTTP 500 | BẤT KỲ smoke test nào trả 500 | Zero tolerance |
| Demo badge missing | Demo case không có `is_demo=true` | Zero tolerance |
| Score < threshold leakage | Real case có `vector_score < 0.55` trong response | Zero tolerance |
| Test suite | < 297/297 pass | Phải 100% |

### 5.2 Soft Gates — Cần > X% để deploy beta

| Gate | Minimum để beta | Minimum để GA |
|---|---|---|
| Manual QA scenarios pass | 12/15 (80%) | 15/15 (100%) |
| API smoke tests pass | 5/5 | 5/5 |
| Frontend smoke tests pass | 20/25 (80%) | 25/25 |
| Retrieval top-1 relevance | ≥ 75% (với data thật) | ≥ 85% |
| Retrieval top-3 relevance | ≥ 85% | ≥ 92% |
| Fallback/demo rate | ≤ 50% (cold data) | ≤ 30% (sau seed) |
| Cross-domain error rate | 0% | 0% |
| Empty response rate | 0% | 0% |
| Avg top-1 score | ≥ 0.55 | ≥ 0.60 |

### 5.3 Beta Readiness Decision

```
Beta = Tất cả Hard Gates PASS
       + Manual QA >= 12/15
       + Smoke tests API 5/5
       + Frontend 20/25
       + 0 P0 bug mới phát sinh trong testing
```

```
GA (General Availability) = Tất cả Hard Gates PASS
                            + Tất cả Soft Gates đạt minimum GA
                            + Retrieval benchmark chạy với real data
                            + 0 unresolved P0/P1 bugs
                            + Load test >= 10 concurrent users without degradation
```

### 5.4 Score Sheet

```
[ ] Hard Gates (6/6 required)
    [ ] P0 contradiction = 0
    [ ] Hallucination = 0
    [ ] HTTP 500 = 0
    [ ] Demo badge correct = 100%
    [ ] Score leakage = 0
    [ ] Test suite 297/297

[ ] Manual QA ___/15
    [ ] S-01 Đất đai có sổ đỏ
    [ ] S-02 Đất đai chưa có sổ đỏ
    [ ] S-03 GCN thu hồi đất
    [ ] S-04 Photo sổ đỏ mất gốc
    [ ] S-05 Hòa giải không thành     ← P0 sensitive
    [ ] S-06 Bên thuê
    [ ] S-07 Bên cho thuê
    [ ] S-08 Nợ lương
    [ ] S-09 Sa thải
    [ ] S-10 Ly hôn có con nhỏ        ← P0 sensitive
    [ ] S-11 HĐ đã ký
    [ ] S-12 HĐ chưa ký (đặt cọc)
    [ ] S-13 Query không dấu
    [ ] S-14 Query đa domain
    [ ] S-15 Query phi pháp lý

[ ] API Smoke ___/5
    [ ] /intelligence/analyze
    [ ] /analysis/evidence-gap
    [ ] /retrieval/laws
    [ ] /retrieval/similar-cases
    [ ] /recommendations/next-best-actions

[ ] Frontend Smoke ___/25 (approx)
    [ ] Analyze page (8 bước)
    [ ] Dashboard (5 bước)
    [ ] Evidence Gap (5 bước)
    [ ] Similar Cases (6 bước)
    [ ] Law Search (4 bước)
    [ ] Loading/Empty/Error (4 scenario)
    [ ] History persistence (7 bước)

[ ] Retrieval Benchmark ___/30 queries
    Top-1 relevance: ___%
    Fallback rate:   ___%
    Cross-domain error: ___%

DECISION: [ ] BETA OK  [ ] GA OK  [ ] BLOCK — list issues below

Issues:
-
-
```

---

## 6. Checklist Execution Notes

- **Tester**: chạy ở môi trường clean — không có data test cũ trong localStorage.
- **Backend**: seed `raw_data/` trước khi chạy retrieval benchmark.
- **Env**: set `LAW_VECTOR_SCORE_THRESHOLD=0.55`, `SIMILAR_CASE_SCORE_THRESHOLD=0.55`, `FUSION_VECTOR_SIGNAL_THRESHOLD=0.55` explicit (không rely on default) để verify env config hoạt động.
- **P0 scenarios** (S-05, S-10): test 2 lần với wording khác nhau để verify không phụ thuộc vào exact phrasing.
- **Recording**: chụp màn hình response cho S-05, S-10 để làm bằng chứng P0 fix.
- **Date**: ghi ngày chạy và version/commit hash vào score sheet.
