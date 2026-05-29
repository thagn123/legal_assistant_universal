# Kế hoạch thực thi nhanh — LexAI Accuracy Sprint
**Ngày thực thi:** 2026-05-29 | **Trạng thái P0:** ✅ Hoàn thành (261/261 tests pass)

---

## Tổng quan

| Task | File(s) | Độ phức tạp | Thứ tự |
|------|---------|------------|-------|
| P1-1: Shared EvidenceContext | session_store + orchestrator + rec_routes | Lớn | 1 |
| P1-2: Similar Cases threshold | retrieval_routes.py | Nhỏ | 2 |
| P1-4: CONTRADICTED clarification | evidence_gap_engine.py | Nhỏ | 3 |
| P2-1: Output validator | output_validator.py (new) + orchestrator | Nhỏ | 4 |
| Tests T02-T04 | test_evidence_gap_accuracy.py | Nhỏ | 5 |
| Regression check | full suite | — | 6 |

---

## Task 1 — P1-1: Shared EvidenceContext per session

**Vấn đề:** Analyze page tính `sổ đỏ=PRESENT` nhưng Dashboard NBA endpoint tính độc lập → recommend "thu thập sổ đỏ". Cần share evidence_context qua session store.

### Bước 1.1 — `src/memory/session_store.py`

**Thêm 3 field vào `SessionContext` dataclass (sau `metadata`):**

```python
# Dòng hiện tại (khoảng dòng 38-47):
@dataclass
class SessionContext:
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    history: List[Dict[str, Any]]
    law_type_preferences: List[str]
    last_query_plan: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
```

**Thay bằng:**

```python
@dataclass
class SessionContext:
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    history: List[Dict[str, Any]]
    law_type_preferences: List[str]
    last_query_plan: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    # Evidence snapshot — shared across modules within same session
    evidence_snapshot: Optional[Dict[str, Any]] = None
    evidence_domain: Optional[str] = None
    evidence_updated_at: Optional[str] = None
```

**Trong `load_context()` — thêm 3 field khi restore từ MongoDB (sau dòng `metadata=doc.get("metadata", {})`):**

```python
            return SessionContext(
                session_id=doc["session_id"],
                user_id=doc["user_id"],
                created_at=doc.get("created_at", now),
                last_active=now,
                history=doc.get("history", []),
                law_type_preferences=doc.get("law_type_preferences", []),
                last_query_plan=doc.get("last_query_plan"),
                metadata=doc.get("metadata", {}),
                evidence_snapshot=doc.get("evidence_snapshot"),
                evidence_domain=doc.get("evidence_domain"),
                evidence_updated_at=doc.get("evidence_updated_at"),
            )
```

**Thêm method `update_evidence_snapshot()` vào class `SessionStore` (sau method `cache_retrieval_context()`):**

```python
    def update_evidence_snapshot(
        self,
        session_id: str,
        user_id: str,
        evidence_snapshot: Dict[str, Any],
        domain: str,
    ) -> None:
        """Persist evidence_context snapshot for cross-module sharing within a session."""
        try:
            self.sessions.update_one(
                {"session_id": session_id, "user_id": user_id},
                {
                    "$set": {
                        "evidence_snapshot": evidence_snapshot,
                        "evidence_domain": domain,
                        "evidence_updated_at": _now(),
                        "last_active": _now(),
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("update_evidence_snapshot failed: %s", exc)
```

---

### Bước 1.2 — `src/engine/orchestrator.py`

**Trong Stage 7 (khoảng dòng 486-512), sau `save_context(...)`, thêm evidence snapshot:**

Tìm đoạn:
```python
            self._session_store.save_context(
                context=session_ctx,
                result_summary=result_summary,
                trace_id=trace_id,
                query_plan=plan.to_dict(),
            )
```

Thêm ngay bên dưới:
```python
            # Save evidence snapshot for cross-module sharing (P1-1)
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

---

### Bước 1.3 — `src/api/recommendation_routes.py`

**Thêm `session_id` vào `NextBestActionRequest` model (khoảng dòng 321):**

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
    session_id: Optional[str] = None   # NEW — để load evidence_snapshot
```

**Trong endpoint `recommend_next_best_actions` (khoảng dòng 420), sau khi build `enriched` list, thêm filter:**

Tìm đoạn `ctx = build_recommendation_context(...)` (khoảng dòng 443) và thêm trước nó:

```python
    # Load evidence snapshot from session to filter contradictory actions (P1-1)
    session_present_evidence: List[Any] = []
    if body.session_id:
        try:
            from src.memory.session_store import SessionStore
            _ss = SessionStore()
            _sctx = _ss.load_context(body.session_id, user_id)
            if _sctx.evidence_snapshot:
                session_present_evidence = _sctx.evidence_snapshot.get("present_evidence", [])
        except Exception as _e:
            logger.debug("NBA: could not load evidence snapshot: %s", _e)
```

Sau đó, ở cuối hàm, trước `return enriched`, thêm filter:

```python
    # Filter recommendations contradicting known-present evidence (P1-1)
    if session_present_evidence:
        from src.evidence.evidence_gap_engine import filter_contradictory_recommendations
        all_descriptions = [d.get("description", "") for d in enriched if isinstance(d, dict)]
        # Filter on journey_steps which are the most likely to contain "thu thập X"
        for item in enriched:
            if hasattr(item, "journey_steps") or isinstance(item, dict):
                steps = item.get("journey_steps", []) if isinstance(item, dict) else getattr(item, "journey_steps", [])
                filtered_steps = filter_contradictory_recommendations(steps, session_present_evidence)
                if isinstance(item, dict):
                    item["journey_steps"] = filtered_steps
                else:
                    object.__setattr__(item, "journey_steps", filtered_steps) if hasattr(item, "__dataclass_fields__") else None

    return enriched
```

> **Lưu ý:** `enriched` là `List[NextBestActionOut]` (Pydantic models, không phải dict). Cần xem lại Pydantic version. Nếu dùng Pydantic v2: dùng `item.model_copy(update={"journey_steps": filtered_steps})`. Nếu v1: `item.journey_steps = filtered_steps`.

**Cách đơn giản hơn (recommended):** Chỉ filter `body.recommended_actions` trước khi build context:

```python
    # Filter recommended_actions contradicting known-present evidence (P1-1)
    effective_recommended_actions = body.recommended_actions
    if body.session_id:
        try:
            from src.memory.session_store import SessionStore
            from src.evidence.evidence_gap_engine import filter_contradictory_recommendations
            _ss = SessionStore()
            _sctx = _ss.load_context(body.session_id, user_id)
            if _sctx.evidence_snapshot:
                present_ev = _sctx.evidence_snapshot.get("present_evidence", [])
                if present_ev:
                    effective_recommended_actions = filter_contradictory_recommendations(
                        body.recommended_actions, present_ev
                    )
        except Exception as _e:
            logger.debug("NBA evidence snapshot load failed: %s", _e)

    ctx = build_recommendation_context(
        situation=body.situation,
        domain=body.domain,
        ...
        recommended_actions=effective_recommended_actions,   # thay body.recommended_actions
        ...
    )
```

---

### Test P1-1

```bash
python -m pytest tests/api/test_recommendation_next_best_action_api.py -q
python -m pytest tests/api/test_evidence_gap_accuracy.py -q
```

---

## Task 2 — P1-2: Similar Cases injection threshold

**Vấn đề:** Demo cases được inject vào top-1 unconditionally — ngay cả khi vector search đã tìm được kết quả tốt, làm mất tính personalied.

**File:** `src/api/retrieval_routes.py` — **dòng 595-606**

**Tìm đoạn:**
```python
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

**Thay bằng:**
```python
    # Inject specialized fallback cases ONLY when retrieval confidence is low
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

**Chỉ thêm 2 dòng bao quanh:** `top_score = ...` và `if fallback_used or top_score < 0.45:` + indent block.

**Test:**
```bash
python -m pytest tests/api/ -q -k "similar"
```

---

## Task 3 — P1-4: CONTRADICTED clarification UX

**Vấn đề:** Tất cả CONTRADICTED items đều dùng câu hỏi generic. Cần câu hỏi cụ thể hơn per evidence type.

**File:** `src/evidence/evidence_gap_engine.py`

**Thêm dict + helper function trước `_build_recommendations()` (khoảng dòng 272):**

```python
_CONTRADICTION_CLARIFICATIONS: Dict[str, str] = {
    "land_certificate": (
        "Sổ đỏ/Giấy chứng nhận QSDĐ của bạn: đang giữ bản gốc, chỉ có photo/bản sao, "
        "hay bản gốc đã bị mất hoặc đang do người khác giữ?"
    ),
    "labor_contract": (
        "Hợp đồng lao động: bạn đang giữ bản gốc có chữ ký, chỉ có bản scan/ảnh chụp, "
        "hay chưa bao giờ được công ty cấp bản giấy?"
    ),
    "marriage_certificate": (
        "Giấy đăng ký kết hôn: đang giữ bản gốc, chỉ có bản sao công chứng, hay đã thất lạc/chưa đăng ký?"
    ),
    "transfer_document": (
        "Giấy chuyển nhượng/mua bán: đang giữ bản gốc có đủ chữ ký các bên, chỉ có photo, "
        "hay giấy chỉ viết tay chưa công chứng?"
    ),
    "payment_proof": (
        "Biên lai/chứng từ thanh toán: bạn có biên nhận gốc, chuyển khoản có sao kê, "
        "hay chỉ thanh toán tiền mặt không có giấy tờ?"
    ),
    "birth_certificate": (
        "Giấy khai sinh: đang giữ bản gốc, chỉ có bản sao công chứng, hay chưa làm giấy khai sinh?"
    ),
}


def _contradiction_clarification(item: EvidenceAssessment) -> str:
    custom = _CONTRADICTION_CLARIFICATIONS.get(item.evidence_id)
    if custom:
        return custom
    return (
        f"Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, bản sao/photo, "
        "hay tài liệu đã bị mất/người khác đang giữ?"
    )
```

**Cập nhật `_build_recommendations()` — thay dòng cho contradicted items:**

Tìm:
```python
    for item in contradicted:
        recommendations.append(
            f"Làm rõ tình trạng {item.title}: bạn đang giữ bản gốc, bản sao hay tài liệu đã bị mất?"
        )
```

Thay bằng:
```python
    for item in contradicted:
        recommendations.append(_contradiction_clarification(item))
```

**Test:**
```python
from src.evidence.evidence_gap_engine import analyze_evidence_gap
result = analyze_evidence_gap("tôi có sổ đỏ nhưng bản gốc bị mất", domain="dat_dai")
assert result.contradictions
assert "bản gốc" in result.recommendations[0]
assert "photo" in result.recommendations[0] or "sao" in result.recommendations[0]
```

---

## Task 4 — P2-1: Output validation layer

**Mục đích:** Lớp bảo vệ cuối cùng — nếu LLM vẫn recommend "thu thập X" dù X=PRESENT, rewrite nó trước khi trả API.

### Bước 4.1 — Tạo file mới `src/engine/output_validator.py`

```python
"""
OutputValidator — post-generation safety layer.

Rewrites recommended_actions that contradict present evidence,
so the LLM hallucination cannot reach the user.
"""

from __future__ import annotations

import logging
from typing import Any, List

from src.evidence.evidence_gap_engine import filter_contradictory_recommendations

logger = logging.getLogger(__name__)


class OutputValidator:
    """Apply filter_contradictory_recommendations to an IntelligenceResult."""

    def validate(
        self,
        recommended_actions: List[str],
        evidence_context: Any,
    ) -> List[str]:
        """
        Rewrite any recommended_action that asks to gather already-present evidence.
        Never blocks the response — always returns a valid list.
        """
        if not evidence_context:
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

### Bước 4.2 — Wiring vào `src/engine/orchestrator.py`

**Thêm import ở đầu file (sau các import hiện có):**
```python
from src.engine.output_validator import OutputValidator
```

**Thêm `self._output_validator = OutputValidator()` trong `__init__` của orchestrator.**

**Trong Stage 7 assembly (khoảng dòng 417-420), thay:**
```python
        recommended_actions = _generate_recommendations(plan, strength, risks, evidence_context)
        recommended_actions = filter_contradictory_recommendations(
            recommended_actions,
            evidence_context.present_evidence,
        )
```

**Thay bằng:**
```python
        recommended_actions = _generate_recommendations(plan, strength, risks, evidence_context)
        recommended_actions = self._output_validator.validate(recommended_actions, evidence_context)
```

> Lưu ý: `OutputValidator.validate()` bên trong đã gọi `filter_contradictory_recommendations()` — không duplicate filter. Xóa import `filter_contradictory_recommendations` ở đầu orchestrator nếu không còn dùng ở chỗ nào khác.

**Test:**
```bash
python -m pytest tests/ -q --tb=short
```

---

## Task 5 — Tests T02, T03, T04

**File:** `tests/api/test_evidence_gap_accuracy.py`

**Thêm 3 test cases sau test hiện có:**

```python
def test_evidence_gap_api_possessive_so_do_cua_toi():
    """T02: 'sổ đỏ của tôi bị tranh chấp' → present_evidence có Sổ đỏ, không có trong missing."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "test_T02"},
            json={"situation": "sổ đỏ của tôi bị tranh chấp bởi hàng xóm", "domain": "dat_dai", "facts": []},
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_titles = {item["item"] for item in body["missing_evidence"]}
    present_titles = {item["item"] for item in body["present_evidence"]}
    assert not any("Sổ đỏ" in t for t in missing_titles), f"Sổ đỏ should not be MISSING, got: {missing_titles}"
    # Present or uncertain (possessive cue detected)
    assert any("Sổ đỏ" in t for t in present_titles) or body["coverage_score"] >= 0.1


def test_evidence_gap_api_labor_possessive():
    """T03: 'hợp đồng lao động của tôi bị vi phạm' → labor_contract in present_evidence."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "test_T03"},
            json={
                "situation": "hợp đồng lao động của tôi bị công ty vi phạm, không báo trước khi sa thải",
                "domain": "lao_dong",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_titles = {item["item"] for item in body["missing_evidence"]}
    present_titles = {item["item"] for item in body["present_evidence"]}
    assert not any("Hợp đồng lao động" in t for t in missing_titles), (
        f"labor_contract should not be MISSING. missing={missing_titles}"
    )


def test_evidence_gap_api_recommendations_no_present_conflict():
    """T04: Recommendations không được chứa 'thu thập/bổ sung X' khi X đã ở PRESENT."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "test_T04"},
            json={
                "situation": (
                    "tôi đã có sổ đỏ và hợp đồng mua bán. "
                    "Hàng xóm tranh chấp ranh giới đất."
                ),
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    recommendations = body.get("recommendations", [])
    present_items = {item["item"] for item in body.get("present_evidence", [])}
    for rec in recommendations:
        for p in present_items:
            # Recommendation không được suggest "thu thập/bổ sung" item đã có
            if any(w in rec.lower() for w in ["thu thập", "bổ sung", "cần có", "cần nộp"]):
                short_p = p.split("/")[0].lower()[:10]
                assert short_p not in rec.lower(), (
                    f"Rec '{rec}' contradicts present item '{p}'"
                )
```

---

## Task 6 — Regression check

Sau khi implement xong tất cả:

```bash
python -m pytest tests/evidence/ tests/api/ tests/recommenders/ -q --tb=short
```

**Expected:** tất cả tests pass, số lượng >= 264 (261 cũ + 3 test mới T02/T03/T04).

---

## Checklist thực thi theo thứ tự

```
□ 1. session_store.py — thêm 3 field vào SessionContext + load_context + update_evidence_snapshot()
□ 2. orchestrator.py  — gọi update_evidence_snapshot() trong Stage 7
□ 3. recommendation_routes.py — thêm session_id + load + filter effective_recommended_actions
□ 4. retrieval_routes.py — thêm top_score threshold check cho injection block
□ 5. evidence_gap_engine.py — thêm _CONTRADICTION_CLARIFICATIONS + _contradiction_clarification()
□ 6. output_validator.py — tạo file mới
□ 7. orchestrator.py — import + self._output_validator + wiring
□ 8. test_evidence_gap_accuracy.py — thêm T02, T03, T04
□ 9. python -m pytest tests/ -q → phải pass
```

---

## Ghi chú quan trọng

- **P1-1 bước 1.3** (NBA endpoint): Phần filter `journey_steps` trên Pydantic model cần cẩn thận. **An toàn nhất:** chỉ filter `effective_recommended_actions` trước khi build context (không động vào enriched list).
- **P2-1:** Nếu muốn đơn giản, bỏ qua file mới — chỉ giữ nguyên `filter_contradictory_recommendations()` trong orchestrator (đã có). File mới chỉ thêm tính tường minh.
- **Thứ tự commit:** Làm P1-1 → test → P1-2 → test → P1-4 + P2-1 → test toàn bộ. Không commit 1 lần hết.
