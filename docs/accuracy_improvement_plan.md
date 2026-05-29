# Accuracy Improvement Plan — LexAI/ULKA
**Ngày:** 2026-05-28 | **Baseline commit:** `3e68d95` | **Mục tiêu:** 5.5/10 → 7.5/10

---

## Tổng quan vấn đề

Người dùng nói "tôi có sổ đỏ" nhưng hệ thống ở module khác vẫn gợi ý "cần thu thập sổ đỏ". Đây là lỗi mất niềm tin nghiêm trọng nhất. Nguyên nhân gốc rễ gồm 3 lớp:

1. **Alias coverage hẹp** — extractor không nhận ra "sổ đỏ của tôi", "GCN QSDĐ" (không dấu), "bìa hồng", v.v.
2. **LLM không bị buộc tôn trọng evidence status** — instruction chưa đủ mạnh
3. **EvidenceContext không được chia sẻ giữa modules** — Analyze, NBA, RAG tính toán độc lập

---

## P0 — Bắt buộc sửa ngay

### P0-1: Mở rộng alias coverage + possessive phrase detection

**Files:**
- `src/evidence/evidence_normalizer.py` — thêm aliases cho `land_certificate`, `transfer_document`, domain aliases mới
- `src/evidence/evidence_extractor.py` — thêm possessive cue (`của tôi`, `đứng tên tôi`, v.v.)

**Lỗi cụ thể:**
- `"sổ đỏ của tôi bị tranh chấp"` → land_cert=UNCERTAIN (sai, nên PRESENT)
- `"tôi có GCN QSDĐ"` → có thể miss vì "đ" vs "d" fold
- `"bìa hồng"` → không có trong alias list

**Aliases cần thêm vào `land_certificate`:**
```python
"bìa hồng", "bia hong",
"giấy chứng thực quyền sử dụng đất",
"giấy nhà đất",
"chứng nhận sử dụng đất",
"giấy cn qsdd",          # no-diacritic variant
"giay cn quyen su dung dat",
```

**Possessive cues cần thêm vào `_POSITIVE_BEFORE` trong extractor:**
```python
"cua toi",               # "của tôi" folded
"cua gia dinh toi",
"do toi dung ten",
"dung ten toi",
"toi dang nam giu",
"nam giu",
```

**Possessive pattern detection trong `_status_for_occurrence()`:**
```python
# Kiểm tra: alias xuất hiện như possessive của người dùng
# VD: "sổ đỏ của tôi" → PRESENT dù không có "đã có" trước
POSSESSIVE_AFTER = ["cua toi", "cua gia dinh toi", "do toi giu", "thuoc ve toi"]
pos_after = _nearest_after(after, POSSESSIVE_AFTER, limit=25)
if pos_after and not neg_before and not neg_after:
    return PRESENT, 0.85, [f"possessive:{pos_after}"]
```

**Domain aliases mới:**
```python
"hinh_su": "hinh_su",
"hinh su": "hinh_su",
"criminal": "hinh_su",
"hanh_chinh": "hanh_chinh",
"hanh chinh": "hanh_chinh",
"administrative": "hanh_chinh",
"khieu nai hanh chinh": "hanh_chinh",
"thua ke": "dan_su",
"di chuc": "dan_su",
"ly hon": "gia_dinh",
"nuoi con": "gia_dinh",
"sa thai": "lao_dong",
"ngo luong": "lao_dong",
```

**Test case để verify P0-1:**
```python
assert extractor("sổ đỏ của tôi bị tranh chấp")["land_certificate"] == PRESENT
assert extractor("tôi có GCN QSDĐ")["land_certificate"] == PRESENT
assert extractor("bìa hồng đứng tên tôi")["land_certificate"] == PRESENT
assert extractor("hàng xóm lấn đất, sổ đỏ của tôi rõ ràng")["land_certificate"] == PRESENT
```

---

### P0-2: Strengthen LLM instruction về evidence-status

**File:** `src/engine/orchestrator.py` — `_SYSTEM_PROMPT`
**File:** `src/llm/prompts.py` — `SITUATION_ANALYSIS_PROMPT`

**Thêm vào `_SYSTEM_PROMPT`:**
```python
## Quy tắc tuyệt đối về chứng cứ (vi phạm = lỗi nghiêm trọng)
Trong USER_FACTS/EVIDENCE_STATUS, mỗi mục có trường "status":
- PRESENT: người dùng xác nhận đã có. TUYỆT ĐỐI không viết "cần thu thập", "bổ sung", "cần có" mục này.
  → Chỉ được gợi ý: kiểm tra tính hợp lệ, bản gốc/bản sao, ngày cấp, tên người đứng trên tài liệu.
- MISSING: mới được đề nghị thu thập.
- CONTRADICTED: phải hỏi làm rõ trước khi đưa ra khuyến nghị về mục này.
- UNCERTAIN: có thể hỏi lại nhẹ nhàng.

Ví dụ SAI (cần tránh):
  User có sổ đỏ (PRESENT) → AI viết "Bạn nên thu thập sổ đỏ để tăng sức mạnh pháp lý"

Ví dụ ĐÚNG:
  User có sổ đỏ (PRESENT) → AI viết "Bạn đã có Sổ đỏ — hãy kiểm tra tên đứng sổ, ngày cấp và giữ bản gốc an toàn."
```

**Thêm explicit evidence instruction vào user_content (orchestrator.py ~line 295):**
```python
if evidence_context.present_evidence:
    titles = [e.title for e in evidence_context.present_evidence[:5]]
    evidence_instruction = (
        "\n\n⚠️ NGƯỜI DÙNG XÁC NHẬN ĐÃ CÓ các tài liệu sau. "
        "KHÔNG được đề nghị thu thập/bổ sung chúng:\n"
        + "\n".join(f"  ✓ {t}" for t in titles)
    )
else:
    evidence_instruction = ""

user_content = (
    f"Tình huống: {situation[:800]}\n\n"
    f"Vai trò: {user_role}\n\n"
    f"USER_FACTS / EVIDENCE_STATUS:\n{evidence_json}"
    f"{evidence_instruction}\n\n"
    f"Bối cảnh pháp lý đã truy xuất:\n{context_snippets}"
)
```

---

### P0-3: Mở rộng `_is_supplement_action()` filter

**File:** `src/evidence/evidence_gap_engine.py`

**Hiện tại:** Chỉ check 9 cụm cố định. Nếu LLM dùng wording khác → filter bỏ qua.

**Fix:**
```python
import re as _re

_SUPPLEMENT_VERB_PATTERNS = [
    r"(bo sung|can bo sung|can chuan bi|chuan bi|thu thap|can thu thap|nop them|cung cap them|can co)",
    r"(nen|can|phai)\s.{0,20}(giay|so|bien lai|hop dong|chung tu|tai lieu)",
    r"viec co\s.{0,30}(la|rat)\s.{0,10}(quan trong|can thiet)",
    r"(xin cap|xin cấp|lam lai|lay them)",
    r"(nen co|hay co|can phai co)",
]

def _is_supplement_action(text: str) -> bool:
    folded = normalize_text(text)
    return any(_re.search(pat, folded) for pat in _SUPPLEMENT_VERB_PATTERNS)
```

**Test case:**
```python
assert _is_supplement_action("Bạn nên có giấy chứng nhận để bảo vệ quyền lợi") == True
assert _is_supplement_action("Việc có được sổ đỏ là rất quan trọng") == True
assert _is_supplement_action("Bạn đã có Sổ đỏ — hãy kiểm tra tính hợp lệ") == False
assert _is_supplement_action("Xác minh bản gốc/bản sao") == False
```

---

## P1 — Cần sửa sớm

### P1-1: Shared EvidenceContext per session (R1 — QA plan)

**Problem:** Analyze, Evidence Gap, NBA, RAG đều compute evidence_context độc lập. Nếu Analyze page compute "sổ đỏ = PRESENT" nhưng Dashboard NBA gọi endpoint riêng không có context → NBA recommend "thu thập sổ đỏ" → contradiction.

**Files:**
- `src/memory/session_store.py` — thêm `evidence_snapshot` field
- `src/engine/orchestrator.py` — save evidence_context vào session sau Stage 1
- `src/api/recommendation_routes.py` — NBA endpoint load evidence từ session

**Schema thêm vào SessionContext:**
```python
@dataclass
class SessionContext:
    session_id: str
    user_id: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    law_type_preferences: List[str] = field(default_factory=list)
    last_active: Optional[str] = None
    # Mới:
    evidence_snapshot: Optional[Dict[str, Any]] = None  # serialized EvidenceGapAnalysis
    evidence_domain: Optional[str] = None
    evidence_updated_at: Optional[str] = None
```

**Orchestrator save (sau Stage 1):**
```python
# Stage 1 end — save evidence snapshot
if evidence_context and session_ctx:
    self._session_store.update_evidence_snapshot(
        sid, user_id,
        evidence_snapshot=evidence_context.to_dict(),
        domain=plan.detected_domain,
    )
```

**NBA endpoint load:**
```python
session_ctx = session_store.load_context(session_id, user_id) if session_id else None
present_evidence = []
if session_ctx and session_ctx.evidence_snapshot:
    snapshot = session_ctx.evidence_snapshot
    present_evidence = snapshot.get("present_evidence", [])
recommended_actions = filter_contradictory_recommendations(actions, present_evidence)
```

**Acceptance criteria:**
- NBA không recommend "thu thập sổ đỏ" sau khi user đã analyze tình huống có sổ đỏ trong cùng session
- Evidence context persist ít nhất theo lifetime của session (24h TTL)

---

### P1-2: Fix Similar Cases injection threshold

**File:** `src/api/retrieval_routes.py`

**Problem:** Inject hardcoded demo case vào top-1 khi không tìm thấy từ khóa, bất kể similarity score kết quả thật là bao nhiêu.

**Fix:**
```python
# Chỉ inject khi retrieval thật sự thất bại (low confidence)
top_score = cases[0].get("similarity_score", 0) if cases else 0
if domain == "lao_dong" and top_score < 0.45 and not any(
    "sa thai" in normalize_text(c.get("title", "")) for c in cases[:3]
):
    cases.insert(0, LABOR_TERMINATION_CASE)
```

**Tương tự cho gia_dinh fallback.**

---

### P1-3: Mở rộng infer_domain_from_text()

**File:** `src/evidence/evidence_normalizer.py`

**Hiện tại:** Chỉ 5 keywords/domain, không detect `hinh_su`, `hanh_chinh`.

**Fix:**
```python
scores = {
    "dat_dai": ["dat", "so do", "quyen su dung dat", "thua dat", "bat dong san", "so hong", "bia do", "gcn qsdd"],
    "gia_dinh": ["ly hon", "nuoi con", "ket hon", "vo chong", "cap duong", "hon nhan", "chia tai san"],
    "lao_dong": ["lao dong", "sa thai", "nghi viec", "bang luong", "bhxh", "hop dong lao dong", "ngo luong"],
    "hop_dong": ["hop dong", "thoa thuan", "phat vi pham", "thanh toan", "vi pham hop dong"],
    "dan_su": ["thua ke", "di chuc", "tai san", "dan su", "chia thua ke", "nguoi thua ke"],
    "hinh_su": ["hinh su", "toi pham", "bi can", "truy to", "bat giam", "canh sat", "vu an hinh su"],
    "hanh_chinh": ["hanh chinh", "quyet dinh hanh chinh", "khieu nai", "ubnd", "co quan hanh chinh"],
    "doanh_nghiep": ["cong ty", "co dong", "pha san", "von dieu le", "hdqt", "giam doc"],
}
```

---

### P1-4: Clarification prompt cho CONTRADICTED items (R5 — QA plan)

**File:** `src/evidence/evidence_gap_engine.py` — `_build_recommendations()`

**Hiện tại:** "Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, bản sao hay tài liệu đã bị mất?"

**Improvement — specific clarification per item type:**
```python
_CONTRADICTION_CLARIFICATIONS = {
    "land_certificate": (
        "Sổ đỏ/Giấy chứng nhận của bạn: đang giữ bản gốc, chỉ có photo/bản sao, "
        "hay bản gốc đã bị mất/ai đang giữ?"
    ),
    "labor_contract": (
        "Hợp đồng lao động: bạn đang giữ bản gốc, chỉ có bản scan, "
        "hay chưa bao giờ được cấp bản giấy?"
    ),
    "marriage_certificate": (
        "Giấy đăng ký kết hôn: đang giữ bản gốc, chỉ có bản sao, hay đã thất lạc?"
    ),
}

def _contradiction_clarification(item: EvidenceAssessment) -> str:
    custom = _CONTRADICTION_CLARIFICATIONS.get(item.evidence_id)
    if custom:
        return custom
    return (
        f"Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, bản sao/photo, "
        "hay tài liệu đã bị mất/ai đang giữ?"
    )
```

---

## P2 — Cải thiện nâng cao

### P2-1: Output validation layer

**File mới:** `src/engine/output_validator.py`

Trước khi trả `IntelligenceResult` cho API:
1. Lấy `present_evidence` từ evidence_context
2. Với mỗi `recommended_action`, check xem có conflict với present item không
3. Log violation (không block response, chỉ warn + rewrite)

```python
class OutputValidator:
    def validate_and_fix(
        self,
        result: IntelligenceResult,
        evidence_context: EvidenceGapAnalysis,
    ) -> IntelligenceResult:
        fixed_actions = filter_contradictory_recommendations(
            result.recommended_actions,
            evidence_context.present_evidence,
        )
        result.recommended_actions = fixed_actions
        return result
```

---

### P2-2: Legal document validity status

- Thêm field `validity_status: str` (hiệu_lực | hết_hiệu_lực | chưa_hiệu_lực) vào chunk schema
- Hiển thị badge warning trong Law Search khi `validity_status == "hết_hiệu_lực"`
- Retrieval reranker giảm score của chunk từ văn bản hết hiệu lực

---

### P2-3: Frontend automated tests (R3 — QA plan)

- Setup Vitest + React Testing Library trong `frontend/`
- Test Evidence Gap: mock API → assert 4 buckets hiển thị đúng
- Assert không có raw enum string (`TITLE`, `CERTIFICATE`, `CONFIRMATION`) trên UI
- Assert present evidence không xuất hiện trong missing group

---

## Regression test suite

Sau mỗi fix, chạy:
```bash
python -m pytest tests/evidence/ tests/api/test_evidence_gap_accuracy.py \
  tests/api/test_recommendation_next_best_action_api.py \
  tests/recommenders/test_next_best_action.py -q
```

**Golden test cases cần có (thêm vào `tests/evidence/test_evidence_extractor.py`):**

| Case | Input | Expected |
|---|---|---|
| Possessive phrase | "sổ đỏ của tôi bị tranh chấp" | land_certificate=PRESENT |
| GCN no-diacritic | "tôi có GCN QSDĐ" | land_certificate=PRESENT |
| Bìa hồng alias | "bìa hồng đứng tên tôi" | land_certificate=PRESENT |
| No positive cue | "sổ đỏ đang bị tranh chấp" | land_certificate=PRESENT (possessive context) |
| Explicit missing | "tôi chưa có sổ đỏ" | land_certificate=MISSING |
| Contradicted | "có sổ đỏ nhưng bản gốc bị mất" | land_certificate=CONTRADICTED |
| No diacritics | "toi co so do" | land_certificate=PRESENT |
| Labor no context | "sa thải không báo trước, tôi có hợp đồng lao động" | labor_contract=PRESENT, termination=MISSING |

---

## Thứ tự triển khai (revised 2026-05-28)

| Ngày | Task | File | Ghi chú |
|---|---|---|---|
| 1-2 | P0-1: alias + possessive | `evidence_normalizer.py`, `evidence_extractor.py` | Không phá regression, chỉ improve |
| 1-2 | P0-2: LLM instruction | `orchestrator.py`, `prompts.py` | Không phá regression, chỉ improve |
| 1-2 | P0-3: filter patterns | `evidence_gap_engine.py` | Không phá regression, chỉ improve |
| 3 | P1-1: Shared EvidenceContext | `session_store.py`, `orchestrator.py`, `recommendation_routes.py` | Thay đổi lớn nhất — cần test kỹ |
| 4 | P1-2: Similar Cases fix | `retrieval_routes.py` | |
| 4 | P1-3 (P1-5): domain aliases | `evidence_normalizer.py` | hinh_su, hanh_chinh, doanh_nghiep |
| 5 | Full test suite + thêm T02, T03, T04 | `tests/evidence/`, `tests/api/` | |
| 6-7 | Manual QA 5 scenarios + fix regression | all | Theo QA plan |
