# Implementation Plan — P0 + P1 Fixes
**Ngày tạo:** 2026-05-29  
**Source audit:** `docs/deep_audit_v2.md`  
**Mục tiêu:** Fix các bug làm mất niềm tin người dùng (P0) và cải thiện retention (P1)

---

## CHECKLIST TỔNG THỂ

```
P0 — Phải xong trước khi mời người dùng thật
  □ P0-1  session_store.py     — 3 field mới + update_evidence_snapshot()
  □ P0-2  orchestrator.py      — gọi update_evidence_snapshot() trong Stage 7
  □ P0-3  recommendation_routes.py — session_id + load + filter trong NBA
  □ P0-4  retrieval_routes.py  — top_score < 0.45 gate cho demo injection
  □ P0-5  frontend/api.ts      — thêm session_id vào getNextBestActions()
  □ P0-6  frontend EvidenceGap.tsx + Dashboard.tsx — truyền session_id
  □ P0-7  tests/regression/    — tạo R01-R09, chạy pass

P1 — Phải xong trước tuần tới
  □ P1-1  output_validator.py  — tạo file mới OutputValidator
  □ P1-2  orchestrator.py      — import + wire OutputValidator
  □ P1-3  evidence_gap_engine.py — _CONTRADICTION_CLARIFICATIONS per type
  □ P1-4  test_evidence_gap_accuracy.py — thêm T02, T03, T04
  □ P1-5  tests/integration/   — test_cross_module_consistency.py
  □ P1-6  Chạy full regression suite, verify ≥224 pass
```

---

## P0-1: `src/memory/session_store.py`

**Mục tiêu:** Lưu evidence_snapshot vào session MongoDB để share cross-module.

### Bước 1.1 — Thêm 3 field vào SessionContext dataclass

Tìm class `SessionContext` (khoảng dòng 38-47). Thêm sau field `metadata`:

```python
# THÊM VÀO CUỐI dataclass SessionContext:
evidence_snapshot: Optional[Dict[str, Any]] = None
evidence_domain: Optional[str] = None
evidence_updated_at: Optional[str] = None
```

### Bước 1.2 — Cập nhật load_context() để restore 3 field mới

Tìm method `load_context()`. Tìm chỗ build `SessionContext(...)` từ MongoDB doc. Thêm 3 field mới vào:

```python
# TRƯỚC (ví dụ):
return SessionContext(
    session_id=doc["session_id"],
    user_id=doc["user_id"],
    created_at=doc.get("created_at", now),
    last_active=doc.get("last_active", now),
    history=doc.get("history", []),
    law_type_preferences=doc.get("law_type_preferences", []),
    last_query_plan=doc.get("last_query_plan"),
    metadata=doc.get("metadata", {}),
)

# SAU — thêm 3 dòng:
return SessionContext(
    session_id=doc["session_id"],
    user_id=doc["user_id"],
    created_at=doc.get("created_at", now),
    last_active=doc.get("last_active", now),
    history=doc.get("history", []),
    law_type_preferences=doc.get("law_type_preferences", []),
    last_query_plan=doc.get("last_query_plan"),
    metadata=doc.get("metadata", {}),
    # NEW:
    evidence_snapshot=doc.get("evidence_snapshot"),
    evidence_domain=doc.get("evidence_domain"),
    evidence_updated_at=doc.get("evidence_updated_at"),
)
```

### Bước 1.3 — Thêm method update_evidence_snapshot()

Thêm vào class `SessionStore`, sau method `save_context()`:

```python
def update_evidence_snapshot(
    self,
    session_id: str,
    user_id: str,
    evidence_snapshot: Dict[str, Any],
    domain: str,
) -> None:
    """Persist evidence_context snapshot for cross-module sharing (non-blocking)."""
    try:
        self.sessions.update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {
                "evidence_snapshot": evidence_snapshot,
                "evidence_domain": domain,
                "evidence_updated_at": _now(),
                "last_active": _now(),
            }},
            upsert=True,
        )
    except Exception as exc:
        logger.warning("update_evidence_snapshot failed: %s", exc)
```

**Kiểm tra:** Chạy `python -m pytest tests/ -q --tb=short` — expect same count.

---

## P0-2: `src/engine/orchestrator.py`

**Mục tiêu:** Lưu evidence_context vào session sau Stage 1 tính toán xong.

### Tìm Stage 7 persist block

Tìm comment `# ── Stage 7: Persist` trong file (khoảng dòng 486-512).  
Tìm dòng gọi `self._session_store.save_context(...)`.

Thêm ngay SAU dòng đó:

```python
# NEW — save evidence snapshot for cross-module sharing
try:
    self._session_store.update_evidence_snapshot(
        session_id=sid,
        user_id=user_id,
        evidence_snapshot=evidence_context.to_dict(),
        domain=plan.detected_domain,
    )
except Exception as exc:
    logger.debug("evidence snapshot save failed (non-fatal): %s", exc)
```

**Quan trọng:** `evidence_context` đã được tính ở Stage 1 dòng 190 — không tính lại.

**Kiểm tra:** `python -m pytest tests/ -q --tb=short` — same count.

---

## P0-3: `src/api/recommendation_routes.py`

**Mục tiêu:** NBA endpoint nhận session_id, load evidence_snapshot, filter contradictory actions.

### Bước 3.1 — Thêm session_id vào NextBestActionRequest

Tìm class `NextBestActionRequest` (khoảng dòng 321-331). Thêm field cuối:

```python
class NextBestActionRequest(BaseModel):
    situation: str
    domain: Optional[str] = None
    position_score: float = 0.0
    domain_confidence: float = 0.0
    citations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=6, ge=1, le=10)
    session_id: Optional[str] = None  # NEW
```

### Bước 3.2 — Filter actions trong endpoint

Tìm function `recommend_next_best_actions` (endpoint handler). Tìm chỗ dùng `body.recommended_actions`.

Thêm block filter TRƯỚC chỗ dùng `body.recommended_actions`:

```python
# NEW — load evidence snapshot from session and filter contradictory actions
effective_recommended_actions = body.recommended_actions
if body.session_id:
    try:
        from src.memory.session_store import SessionStore
        from src.evidence.evidence_gap_engine import filter_contradictory_recommendations
        _ss = SessionStore()
        _sctx = _ss.load_context(body.session_id, user_id)
        if _sctx and _sctx.evidence_snapshot:
            present_ev = _sctx.evidence_snapshot.get("present_evidence", [])
            if present_ev:
                effective_recommended_actions = filter_contradictory_recommendations(
                    body.recommended_actions, present_ev
                )
    except Exception as _e:
        logger.debug("NBA evidence snapshot load failed (non-fatal): %s", _e)
```

### Bước 3.3 — Dùng effective_recommended_actions thay vì body.recommended_actions

Trong cùng function đó, thay thế `body.recommended_actions` bằng `effective_recommended_actions` ở bất kỳ chỗ nào nó được dùng để **build NBA context** (không phải type definition).

**Kiểm tra:** `python -m pytest tests/ -q --tb=short` — same count.

---

## P0-4: `src/api/retrieval_routes.py`

**Mục tiêu:** Không inject demo case khi vector search đã có kết quả đủ tốt.

### Tìm block cần sửa (khoảng dòng 595-606)

```python
# TRƯỚC (hiện tại):
# Inject highly specialized fallback cases for domain accuracy and testing assertions compatibility
cases_pool = _FALLBACK_CASES_EN if query_language == "en" else _FALLBACK_CASES
if query_language == "en":
    if domain == "lao_dong" and not any("severance" in c.get("situation_summary", "").lower() for c in raw):
        raw.insert(0, cases_pool[1])
    elif domain in ("gia_dinh", "dan_su") and not any("custody" in c.get("situation_summary", "").lower() for c in raw):
        raw.insert(0, cases_pool[0])
else:
    if domain in ("gia_dinh", "dan_su") and not any("36 tháng" in c.get("situation_summary", "") for c in raw):
        raw.insert(0, cases_pool[0])
    elif domain == "lao_dong" and not any("sa thải" in c.get("situation_summary", "").lower() for c in raw):
        raw.insert(0, cases_pool[1])
```

```python
# SAU (thêm threshold gate):
top_score = raw[0].get("vector_score", 0.0) if raw else 0.0
if fallback_used or top_score < 0.45:
    cases_pool = _FALLBACK_CASES_EN if query_language == "en" else _FALLBACK_CASES
    if query_language == "en":
        if domain == "lao_dong" and not any("severance" in c.get("situation_summary", "").lower() for c in raw):
            raw.insert(0, cases_pool[1])
        elif domain in ("gia_dinh", "dan_su") and not any("custody" in c.get("situation_summary", "").lower() for c in raw):
            raw.insert(0, cases_pool[0])
    else:
        if domain in ("gia_dinh", "dan_su") and not any("36 tháng" in c.get("situation_summary", "") for c in raw):
            raw.insert(0, cases_pool[0])
        elif domain == "lao_dong" and not any("sa thải" in c.get("situation_summary", "").lower() for c in raw):
            raw.insert(0, cases_pool[1])
```

**Kiểm tra:** `python -m pytest tests/ -q --tb=short` — same count.

---

## P0-5 + P0-6: Frontend

### P0-5: `frontend/src/lib/api.ts`

Tìm function `getNextBestActions` (hoặc tương đương). Thêm `session_id` vào params và body:

```typescript
// Tìm interface/type của params (thêm field):
interface NextBestActionParams {
  situation: string;
  domain?: string;
  position_score?: number;
  domain_confidence?: number;
  citations?: string[];
  warnings?: string[];
  recommended_actions?: string[];
  risk_assessment?: Record<string, unknown>;
  limit?: number;
  session_id?: string;  // NEW
}

// Trong function body, thêm vào request JSON:
body: JSON.stringify({
  situation: params.situation,
  domain: params.domain,
  // ... other fields ...
  session_id: params.session_id,  // NEW
}),
```

### P0-6a: `frontend/src/pages/EvidenceGap.tsx`

Tìm chỗ gọi `getNextBestActions(...)`. Thêm `session_id`:

```typescript
// Lấy session_id từ analysisContext hoặc state
const sessionId = currentSessionId || '';  // lấy từ context hoặc state

const actions = await getNextBestActions({
  situation,
  domain,
  session_id: sessionId,  // NEW
  // ... other params
});
```

### P0-6b: `frontend/src/pages/Dashboard.tsx`

Tương tự — tìm chỗ gọi `getNextBestActions()` trong Dashboard, thêm `session_id`.

**Kiểm tra:** DevTools network tab — request body của NBA call phải có `session_id` field.

---

## P0-7: Regression Tests

### Tạo file mới: `tests/regression/__init__.py`
(file rỗng)

### Tạo file mới: `tests/regression/test_evidence_regression.py`

```python
from __future__ import annotations

from src.evidence.evidence_extractor import aggregate_evidence_facts, extract_evidence_facts
from src.evidence.evidence_gap_engine import analyze_evidence_gap
from src.evidence.evidence_schemas import CONTRADICTED, MISSING, PRESENT, UNCERTAIN


def _status(text: str, evidence_id: str, domain: str) -> str:
    facts = aggregate_evidence_facts(extract_evidence_facts(text, domain=domain))
    if evidence_id not in facts:
        return MISSING
    return facts[evidence_id].status


# ── R01-R07: Evidence status regressions ─────────────────────────────────────

def test_r01_so_do_present():
    """R01: 'Tôi đã có sổ đỏ' → land_certificate = PRESENT"""
    assert _status("Tôi đã có sổ đỏ", "land_certificate", "dat_dai") == PRESENT


def test_r02_possessive_so_do_present():
    """R02: 'Sổ đỏ của tôi bị tranh chấp' → land_certificate = PRESENT"""
    assert _status("Sổ đỏ của tôi bị tranh chấp", "land_certificate", "dat_dai") == PRESENT


def test_r03_gcn_qsdd_alias_present():
    """R03: 'Tôi có GCN QSDĐ' → land_certificate = PRESENT"""
    assert _status("Tôi có GCN QSDĐ", "land_certificate", "dat_dai") == PRESENT


def test_r04_chua_co_so_do_missing():
    """R04: 'Tôi chưa có sổ đỏ' → land_certificate = MISSING"""
    assert _status("Tôi chưa có sổ đỏ", "land_certificate", "dat_dai") == MISSING


def test_r05_photo_only_contradicted():
    """R05: 'chỉ có bản photo, mất bản gốc' → CONTRADICTED hoặc UNCERTAIN (phải hỏi lại)"""
    result = _status("Tôi chỉ có bản photo sổ đỏ, bản gốc đã bị mất", "land_certificate", "dat_dai")
    assert result in (CONTRADICTED, UNCERTAIN), f"Expected CONTRADICTED/UNCERTAIN, got {result}"


def test_r06_labor_contract_possessive_present():
    """R06: 'Hợp đồng lao động của tôi bị vi phạm' → labor_contract = PRESENT"""
    assert _status("Hợp đồng lao động của tôi bị vi phạm", "labor_contract", "lao_dong") == PRESENT


def test_r07_marriage_cert_possessive_present():
    """R07: 'Giấy đăng ký kết hôn của chúng tôi' → marriage_certificate = PRESENT"""
    result = _status(
        "Giấy đăng ký kết hôn của chúng tôi vẫn còn hiệu lực",
        "marriage_certificate",
        "gia_dinh",
    )
    assert result == PRESENT


# ── R08-R09: Recommendation regressions ──────────────────────────────────────

_SUPPLEMENT_PATTERNS = [
    "xin cấp sổ đỏ lần đầu",
    "thu thập sổ đỏ",
    "bổ sung sổ đỏ",
    "cần có sổ đỏ",
    "nộp thêm sổ đỏ",
]


def test_r08_no_supplement_recommend_when_present():
    """R08: situation có sổ đỏ → không recommend thu thập sổ đỏ"""
    situations = [
        "Tôi đã có sổ đỏ, hàng xóm lấn 50cm đất của tôi",
        "Sổ đỏ của tôi bị hàng xóm tranh chấp",
        "GCN QSDĐ đứng tên tôi, đang bị tranh chấp",
    ]
    for s in situations:
        result = analyze_evidence_gap(s, "dat_dai")
        for rec in result.recommendations:
            for pat in _SUPPLEMENT_PATTERNS:
                assert pat.lower() not in rec.lower(), (
                    f"REGRESSION R08: '{s}' produced bad recommendation: '{rec}'"
                )


def test_r09_reconciled_recommends_lawsuit_not_mediation():
    """R09: đã hòa giải không thành → recommendations không gợi ý hòa giải lại"""
    result = analyze_evidence_gap(
        "Tôi đã hòa giải tại UBND xã nhưng không thành công, hai bên không đồng ý",
        "dat_dai",
    )
    recs_text = " ".join(result.recommendations).lower()
    # Không được chỉ nói "hòa giải tại UBND" như bước đầu tiên
    # Có thể nhắc đến hòa giải trong ngữ cảnh "đã hòa giải" nhưng recommend phải là khởi kiện
    assert "hòa giải tại ubnd xã" not in recs_text or "không thành" in recs_text


# ── Chạy toàn bộ ─────────────────────────────────────────────────────────────
# python -m pytest tests/regression/ -q --tb=short
```

**Kiểm tra:**
```bash
python -m pytest tests/regression/ -q --tb=short
# Expect: 9 passed
```

---

## P1-1: `src/engine/output_validator.py` (NEW FILE)

**Mục tiêu:** Safety layer sau LLM generation — rewrite actions mâu thuẫn với PRESENT evidence.

```python
from __future__ import annotations

import logging
from typing import Any, List

from src.evidence.evidence_gap_engine import filter_contradictory_recommendations

logger = logging.getLogger(__name__)


class OutputValidator:
    """
    Post-generation safety layer.
    Rewrites recommended_actions that conflict with PRESENT evidence.
    Never raises — on any error, returns original actions unchanged.
    """

    def validate(
        self,
        recommended_actions: List[str],
        evidence_context: Any,
    ) -> List[str]:
        if not evidence_context or not recommended_actions:
            return recommended_actions
        present = getattr(evidence_context, "present_evidence", [])
        if not present:
            return recommended_actions
        try:
            return filter_contradictory_recommendations(recommended_actions, present)
        except Exception as exc:
            logger.warning("OutputValidator failed (non-fatal): %s", exc)
            return recommended_actions
```

---

## P1-2: Wire OutputValidator vào orchestrator

Tìm chỗ `recommended_actions` được tạo trong `orchestrator.py` (khoảng dòng 417-420). Sau khi tạo xong list:

```python
# Thêm import ở đầu file (cùng block với các import khác):
from src.engine.output_validator import OutputValidator

# Trong __init__:
self._output_validator = OutputValidator()

# Tìm chỗ recommended_actions được build, thêm sau:
recommended_actions = self._output_validator.validate(recommended_actions, evidence_context)
```

**Kiểm tra:** `python -m pytest tests/ -q --tb=short` — same count.

---

## P1-3: `src/evidence/evidence_gap_engine.py` — CONTRADICTED clarification per type

### Thêm dict và helper function (thêm trước `_build_recommendations`):

```python
_CONTRADICTION_CLARIFICATIONS: Dict[str, str] = {
    "land_certificate": (
        "Sổ đỏ/Giấy chứng nhận QSDĐ của bạn: đang giữ bản gốc, "
        "chỉ có photo/bản sao, hay bản gốc đã bị mất hoặc đang do người khác giữ?"
    ),
    "labor_contract": (
        "Hợp đồng lao động: bạn đang giữ bản gốc có chữ ký, "
        "chỉ có bản scan/ảnh chụp, hay chưa bao giờ được công ty cấp bản giấy?"
    ),
    "marriage_certificate": (
        "Giấy đăng ký kết hôn: đang giữ bản gốc, "
        "chỉ có bản sao công chứng, hay đã thất lạc/chưa đăng ký?"
    ),
    "transfer_document": (
        "Giấy chuyển nhượng/mua bán: đang giữ bản gốc có đủ chữ ký các bên, "
        "chỉ có photo, hay giấy chỉ viết tay chưa công chứng?"
    ),
    "payment_proof": (
        "Biên lai/chứng từ thanh toán: bạn có biên nhận gốc, "
        "chuyển khoản có sao kê, hay chỉ thanh toán tiền mặt không có giấy tờ?"
    ),
    "birth_certificate": (
        "Giấy khai sinh: đang giữ bản gốc, "
        "chỉ có bản sao công chứng, hay chưa làm giấy khai sinh?"
    ),
}


def _contradiction_clarification(item: EvidenceAssessment) -> str:
    custom = _CONTRADICTION_CLARIFICATIONS.get(item.evidence_id)
    if custom:
        return custom
    return (
        f"Làm rõ tình trạng {item.title}: "
        "bạn đang giữ bản gốc, bản sao/photo, "
        "hay tài liệu đã bị mất/người khác đang giữ?"
    )
```

### Cập nhật `_build_recommendations()`:

```python
def _build_recommendations(...) -> List[str]:
    recommendations: List[str] = []
    for item in contradicted:
        # TRƯỚC: recommendations.append(f"Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, bản sao hay tài liệu đã bị mất?")
        # SAU:
        recommendations.append(_contradiction_clarification(item))
    # ... phần còn lại giữ nguyên
```

---

## P1-4: `tests/api/test_evidence_gap_accuracy.py` — thêm T02, T03, T04

```python
def test_evidence_gap_api_possessive_so_do_cua_toi():
    """T02: 'sổ đỏ của tôi' → land_certificate không được ở missing_evidence"""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t02_user"},
            json={
                "situation": "sổ đỏ của tôi bị hàng xóm tranh chấp",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_ids = {item["evidence_id"] for item in body["missing_evidence"]}
    present_ids = {item["evidence_id"] for item in body["present_evidence"]}
    assert "land_certificate" not in missing_ids, "land_certificate không được ở missing khi có possessive"
    assert "land_certificate" in present_ids, "land_certificate phải ở present với possessive phrase"


def test_evidence_gap_api_labor_possessive():
    """T03: 'hợp đồng lao động của tôi' → labor_contract không ở missing"""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t03_user"},
            json={
                "situation": "hợp đồng lao động của tôi bị vi phạm nghiêm trọng",
                "domain": "lao_dong",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_ids = {item["evidence_id"] for item in body["missing_evidence"]}
    present_ids = {item["evidence_id"] for item in body["present_evidence"]}
    assert "labor_contract" not in missing_ids
    assert "labor_contract" in present_ids


def test_evidence_gap_api_recommendations_no_present_conflict():
    """T04: recommendations không gợi ý thu thập evidence đã PRESENT"""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t04_user"},
            json={
                "situation": "Tôi đã có sổ đỏ và biên lai chuyển khoản, hàng xóm lấn đất",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    recs = " ".join(body.get("recommendations", [])).lower()
    # Không được recommend thu thập các tài liệu đã PRESENT
    BAD = ["thu thập sổ đỏ", "bổ sung sổ đỏ", "xin cấp sổ đỏ", "cần có sổ đỏ",
           "thu thập biên lai", "bổ sung biên lai", "nộp thêm biên lai"]
    for bad in BAD:
        assert bad not in recs, f"T04: bad recommendation found: '{bad}' in '{recs[:200]}'"
```

---

## P1-5: `tests/integration/test_cross_module_consistency.py` (NEW FILE)

```python
"""
Integration: kiểm tra cross-module consistency — Analyze → NBA không mâu thuẫn.
Chỉ chạy khi use_mongodb=False (mock session store).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_evidence_gap_recommend_no_conflict_with_present():
    """
    Khi evidence_gap trả về present_evidence có 'land_certificate',
    recommendations không được chứa các cụm từ thu thập sổ đỏ.
    """
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        headers = {"X-User-ID": "integration_test_001"}
        resp = client.post(
            "/analysis/evidence-gap",
            headers=headers,
            json={
                "situation": "Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()

    present_ids = {item["evidence_id"] for item in body["present_evidence"]}
    assert "land_certificate" in present_ids, "land_certificate phải PRESENT"

    BAD_PATTERNS = ["thu thập sổ đỏ", "bổ sung sổ đỏ", "xin cấp sổ đỏ", "cần có sổ đỏ"]
    recs = " ".join(body.get("recommendations", [])).lower()
    for bad in BAD_PATTERNS:
        assert bad not in recs, f"Found contradictory recommendation: '{bad}'"


def test_nba_request_accepts_session_id_field():
    """NextBestActionRequest model phải chấp nhận session_id field không bị 422."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "integration_test_002"},
            json={
                "situation": "Tôi đã có sổ đỏ",
                "domain": "dat_dai",
                "session_id": "test_session_123",
                "recommended_actions": ["Thu thập sổ đỏ"],
            },
        )
    # Must not fail with 422 (validation error)
    assert resp.status_code != 422, f"422 means session_id field not accepted: {resp.json()}"
    assert resp.status_code == 200
```

---

## Lệnh kiểm tra cuối cùng

```bash
# Sau khi hoàn thành P0:
python -m pytest tests/regression/ -q --tb=short
# → Expect: 9 passed

# Sau khi hoàn thành P1:
python -m pytest tests/evidence/ tests/api/ tests/recommenders/ tests/regression/ tests/integration/ -q --tb=short
# → Expect: ≥233 passed (224 + 9 regression + T02,T03,T04 + integration)

# Full suite:
python -m pytest tests/ -q --tb=short
# → Expect: ≥237 passed, 0 failed
```

---

## Timeline

| Ngày | Task | File(s) |
|---|---|---|
| Sáng ngày 1 | P0-1, P0-2 | `session_store.py`, `orchestrator.py` |
| Chiều ngày 1 | P0-3, P0-4 | `recommendation_routes.py`, `retrieval_routes.py` |
| Tối ngày 1 | P0-5, P0-6 | `api.ts`, `EvidenceGap.tsx`, `Dashboard.tsx` |
| Sáng ngày 2 | P0-7 regression tests | `tests/regression/` |
| Chiều ngày 2 | P1-1, P1-2 | `output_validator.py`, `orchestrator.py` |
| Tối ngày 2 | P1-3, P1-4, P1-5 | `evidence_gap_engine.py`, test files |
| Ngày 3 | Chạy full suite, fix regression nếu có | all |
