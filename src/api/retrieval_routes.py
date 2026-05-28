from __future__ import annotations

import logging
import re
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.api.deps import require_user
from src.services.situation_classifier import SituationClassifier

logger = logging.getLogger(__name__)

retrieval_router = APIRouter(prefix="/retrieval", tags=["retrieval"])

_classifier = SituationClassifier()

_DOMAIN_LABELS: dict[str, str] = {
    "dat_dai": "Đất đai",
    "hop_dong": "Hợp đồng",
    "lao_dong": "Lao động",
    "doanh_nghiep": "Doanh nghiệp",
    "dan_su": "Dân sự",
    "hinh_su": "Hình sự",
    "hanh_chinh": "Hành chính",
    "gia_dinh": "Gia đình",
    "general": "Tổng hợp",
}

_STAGE_LABELS: dict[str, str] = {
    "preparation": "Chuẩn bị",
    "dispute": "Tranh chấp",
    "negotiation": "Thương lượng",
    "violation": "Vi phạm",
    "pre_litigation": "Chuẩn bị khởi kiện",
    "in_litigation": "Đang khởi kiện",
    "appeal": "Kháng cáo",
    "enforcement": "Thi hành án",
    "contract_signing": "Ký hợp đồng",
    "contract_review": "Soát hợp đồng",
}


# ── Pydantic models ───────────────────────────────────────────────────────────


class SimilarCaseRequest(BaseModel):
    situation: str = Field(..., min_length=10)
    domain_hint: Optional[str] = None
    facts: List[str] = []
    limit: int = Field(default=6, ge=1, le=20)


class SimilarCaseItem(BaseModel):
    case_id: str
    title: str
    situation_summary: str
    outcome: str
    lesson: str
    domain: str
    domain_label: str
    key_laws: List[str]
    similarity_score: float
    similarity_label: str
    stage: str
    stage_label: str


class SimilarCasesResponse(BaseModel):
    request_id: str
    feature: str = "similar_case_explorer"
    query_domain: str
    query_domain_label: str
    query_stage: str
    query_stage_label: str
    similar_cases: List[SimilarCaseItem]
    total: int
    search_mode: str
    summary: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _similarity_label(score: float) -> str:
    if score >= 0.85:
        return "Rất tương đồng"
    if score >= 0.70:
        return "Khá tương đồng"
    if score >= 0.55:
        return "Tương đồng một phần"
    return "Có điểm chung"


def _get_vector_storage(request: Request):
    if getattr(request.app.state, "mongodb_enabled", True) is False:
        return None
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is not None:
        return vs
    try:
        from src.mongodb.mongo_storage import VectorStorage
        return VectorStorage()
    except Exception as exc:
        logger.warning("Mongo vector storage unavailable; using demo fallback data: %s", exc)
        return None
    return vs


def _keywords(text: str, min_len: int = 3, limit: int = 10) -> list[str]:
    folded = text.lower()
    return [w for w in re.findall(r"[\wÀ-ỹ]+", folded, flags=re.UNICODE) if len(w) >= min_len][:limit]


def _ranked_fallback(items: list[dict[str, Any]], query: str, text_fields: list[str], limit: int) -> list[dict[str, Any]]:
    keys = _keywords(query, min_len=3, limit=12)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        haystack = " ".join(str(item.get(field, "")) for field in text_fields).lower()
        hits = sum(1 for key in keys if key in haystack)
        score = 0.42 + min(0.45, hits * 0.09)
        ranked.append((score, {**item, "vector_score": round(score, 3)}))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:limit]]


_FALLBACK_LAWS: list[dict[str, Any]] = [
    {
        "chunk_id": "demo_law_hngd_81",
        "doc_id": "demo_law_hon_nhan_gia_dinh",
        "law_reference": "Luat Hon nhan va Gia dinh 2014, Dieu 81",
        "law_type": "dan_su",
        "is_global": True,
        "content": "Khi ly hon, viec trong nom, cham soc, nuoi duong, giao duc con duoc uu tien theo loi ich moi mat cua con. Con tu du bay tuoi tro len duoc xem xet nguyen vong.",
    },
    {
        "chunk_id": "demo_law_hngd_59",
        "doc_id": "demo_law_hon_nhan_gia_dinh",
        "law_reference": "Luat Hon nhan va Gia dinh 2014, Dieu 59",
        "law_type": "dan_su",
        "is_global": True,
        "content": "Tai san chung cua vo chong khi ly hon duoc chia theo nguyen tac chia doi nhung co tinh den hoan canh gia dinh, cong suc dong gop, loi cua moi ben va bao ve quyen loi chinh dang.",
    },
    {
        "chunk_id": "demo_law_ld_36",
        "doc_id": "demo_law_lao_dong",
        "law_reference": "Bo luat Lao dong 2019, Dieu 36",
        "law_type": "lao_dong",
        "is_global": True,
        "content": "Nguoi su dung lao dong chi duoc don phuong cham dut hop dong lao dong trong cac truong hop luat dinh va phai bao truoc theo thoi han tuong ung.",
    },
    {
        "chunk_id": "demo_law_ds_328",
        "doc_id": "demo_law_dan_su",
        "law_reference": "Bo luat Dan su 2015, Dieu 328",
        "law_type": "dan_su",
        "is_global": True,
        "content": "Dat coc la viec mot ben giao cho ben kia mot khoan tien hoac tai san trong mot thoi han de bao dam giao ket hoac thuc hien hop dong.",
    },
    {
        "chunk_id": "demo_law_dd_188",
        "doc_id": "demo_law_dat_dai",
        "law_reference": "Luat Dat dai 2013, Dieu 188",
        "law_type": "dat_dai",
        "is_global": True,
        "content": "Nguoi su dung dat duoc chuyen nhuong, tang cho, the chap khi co giay chung nhan, dat khong tranh chap, quyen su dung dat khong bi ke bien va con thoi han su dung.",
    },
]

_FALLBACK_CASES: list[dict[str, Any]] = [
    {
        "case_id": "demo_case_divorce_custody",
        "title": "Tranh chap ly hon, nuoi con va chia tai san chung",
        "situation_summary": "Mot ben yeu cau ly hon, muon truc tiep nuoi con nho va tranh chap ve tai san chung hinh thanh trong hon nhan.",
        "outcome": "Toa an xem xet loi ich cua con, kha nang cham soc, thu nhap, cho o va cong suc dong gop vao tai san chung.",
        "lesson": "Can chuan bi chung cu ve thu nhap, dieu kien cham soc con, nguon goc tai san va qua trinh dong gop.",
        "law_type": "dan_su",
        "key_laws": ["Luat HNGD Dieu 59", "Luat HNGD Dieu 81"],
        "stage": "pre_litigation",
    },
    {
        "case_id": "demo_case_labor_termination",
        "title": "Nguoi lao dong bi cham dut hop dong khong bao truoc",
        "situation_summary": "Cong ty cho nghi viec, chua thanh toan luong va khong co van ban giai thich ly do cham dut hop dong.",
        "outcome": "Nguoi lao dong co the yeu cau thanh toan luong, boi thuong va chung minh viec cham dut trai quy dinh.",
        "lesson": "Luu hop dong, bang luong, email, tin nhan va thong bao cham dut la chung cu quan trong.",
        "law_type": "lao_dong",
        "key_laws": ["Bo luat Lao dong 2019"],
        "stage": "violation",
    },
    {
        "case_id": "demo_case_land_handwritten",
        "title": "Mua ban dat bang giay tay phat sinh tranh chap",
        "situation_summary": "Ben mua da giao tien, nhan dat nhung giao dich chua cong chung va ben ban doi lai dat.",
        "outcome": "Co quan giai quyet xem xet thoi diem giao dich, chung cu thanh toan, quan ly su dung dat va dieu kien chuyen nhuong.",
        "lesson": "Can tap hop giay tay mua ban, bien nhan, sao ke, nguoi lam chung va hien trang su dung dat.",
        "law_type": "dat_dai",
        "key_laws": ["Luat Dat dai Dieu 188", "Bo luat Dan su"],
        "stage": "dispute",
    },
]

_FALLBACK_CLAUSES: list[dict[str, Any]] = [
    {
        "clause_id": "demo_clause_penalty",
        "doc_id": "demo_contract",
        "clause_text": "Ben vi pham phai chiu phat vi pham va boi thuong thiet hai thuc te phat sinh theo chung cu hop le.",
        "clause_type": "penalty",
        "risk_level": "medium",
        "suggestion": "Nen neu muc phat, cach tinh thiet hai, chung tu chung minh va thoi han thanh toan.",
    },
    {
        "clause_id": "demo_clause_termination",
        "doc_id": "demo_contract",
        "clause_text": "Moi ben co quyen cham dut hop dong khi ben con lai vi pham nghiem trong va khong khac phuc trong thoi han thong bao.",
        "clause_type": "termination",
        "risk_level": "low",
        "suggestion": "Bo sung quy trinh thong bao, thoi han khac phuc va nghia vu sau cham dut.",
    },
]


# ── Law search models ─────────────────────────────────────────────────────────


class LawSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    domain_hint: Optional[str] = None
    limit: int = Field(default=8, ge=1, le=20)


class LawArticle(BaseModel):
    chunk_id: str
    doc_id: str
    law_reference: str
    content: str
    snippet: str
    law_type: str
    law_type_label: str
    relevance_score: float
    is_global: bool


class LawSearchResponse(BaseModel):
    request_id: str
    feature: str = "law_retrieval"
    query: str
    detected_domain: str
    detected_domain_label: str
    results: List[LawArticle]
    total: int
    search_mode: str
    summary: str


# ── Law search endpoint ───────────────────────────────────────────────────────


@retrieval_router.post("/laws", response_model=LawSearchResponse)
def search_laws(
    body: LawSearchRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> LawSearchResponse:
    """
    Tìm kiếm điều luật liên quan theo truy vấn ngữ nghĩa.
    Tự động phát hiện lĩnh vực, embed truy vấn rồi tìm kiếm vector (fallback: keyword).
    Kết quả gồm nội dung điều luật, mã điều, độ liên quan.
    """
    # Detect domain from query
    profile = _classifier.classify(situation=body.query, domain_hint=body.domain_hint)
    domain = profile.domain if body.domain_hint is None else body.domain_hint

    vs = _get_vector_storage(request)

    search_mode = "vector"
    try:
        from src.pipeline.embedding_stage import embed_text
        embedding = embed_text(body.query)
    except Exception:
        embedding = None

    raw = []
    if embedding and vs is not None:
        try:
            raw = vs.vector_search_chunks(
                query_vector=embedding,
                filter_user_id=user_id,
                law_type=domain if domain != "general" else None,
                limit=body.limit,
            )
            if len(raw) < 2 and domain != "general":
                raw = vs.vector_search_chunks(
                    query_vector=embedding,
                    filter_user_id=user_id,
                    limit=body.limit,
                )
        except Exception as e:
            logger.warning("Vector search chunks failed: %s. Falling back to keyword search.", e)
            raw = []

    if not embedding or not raw:
        search_mode = "keyword"
        keywords = [w for w in body.query.split() if len(w) >= 3][:8]
        if vs is not None:
            try:
                raw = vs.keyword_search_chunks(keywords=keywords, filter_user_id=user_id, limit=body.limit)
            except Exception as exc:
                logger.warning("Keyword search chunks failed: %s. Using demo fallback.", exc)
                raw = []
        if not raw:
            search_mode = "demo_fallback"
            raw = _ranked_fallback(
                [item for item in _FALLBACK_LAWS if domain == "general" or item.get("law_type") == domain] or _FALLBACK_LAWS,
                body.query,
                ["law_reference", "content", "law_type"],
                body.limit,
            )

    articles: list[LawArticle] = []
    for c in raw[: body.limit]:
        content = c.get("content", "")
        snippet = content[:300].rstrip() + ("…" if len(content) > 300 else "")
        c_type = c.get("law_type", domain)
        articles.append(
            LawArticle(
                chunk_id=c.get("chunk_id", ""),
                doc_id=c.get("doc_id", ""),
                law_reference=c.get("law_reference", c.get("article_ref", "")),
                content=content,
                snippet=snippet,
                law_type=c_type,
                law_type_label=_DOMAIN_LABELS.get(c_type, c_type),
                relevance_score=round(float(c.get("vector_score", 0.5)), 3),
                is_global=bool(c.get("is_global", False)),
            )
        )

    count = len(articles)
    if count == 0:
        summary = "Không tìm thấy điều luật phù hợp. Hãy thử từ khóa khác hoặc mô tả chi tiết hơn."
    else:
        top = articles[0]
        summary = (
            f"Tìm thấy {count} điều luật liên quan trong lĩnh vực "
            f"{_DOMAIN_LABELS.get(domain, domain)}. "
            f"Kết quả phù hợp nhất: {top.law_reference or 'Điều luật số 1'}."
        )

    return LawSearchResponse(
        request_id="law_" + str(uuid.uuid4())[:8],
        query=body.query,
        detected_domain=domain,
        detected_domain_label=_DOMAIN_LABELS.get(domain, domain),
        results=articles,
        total=count,
        search_mode=search_mode,
        summary=summary,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────


@retrieval_router.post("/similar-cases", response_model=SimilarCasesResponse)
def find_similar_cases(
    body: SimilarCaseRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> SimilarCasesResponse:
    """
    Tìm vụ việc pháp lý tương tự dựa trên mô tả tình huống.
    Tự động phát hiện lĩnh vực, tìm kiếm vector (fallback: keyword),
    trả về danh sách case có độ tương đồng cao nhất.
    """
    # Step 1: classify to detect domain + stage
    profile = _classifier.classify(
        situation=body.situation,
        facts=body.facts,
        domain_hint=body.domain_hint,
    )
    domain = profile.domain
    stage = profile.stage

    vs = _get_vector_storage(request)

    # Step 2: embed + vector search (fallback to keyword)
    search_mode = "vector"
    try:
        from src.pipeline.embedding_stage import embed_text
        embedding = embed_text(body.situation)
    except Exception:
        embedding = None

    raw = []
    if embedding and vs is not None:
        try:
            raw = vs.vector_search_cases(
                query_vector=embedding,
                law_type=domain if domain != "general" else None,
                limit=body.limit,
            )
            # If vector search returned too few, try without domain filter
            if len(raw) < 2 and domain != "general":
                raw = vs.vector_search_cases(
                    query_vector=embedding,
                    law_type=None,
                    limit=body.limit,
                )
        except Exception as e:
            logger.warning("Vector search cases failed: %s. Falling back to keyword search.", e)
            raw = []

    if not embedding or not raw:
        search_mode = "keyword"
        # Extract meaningful keywords from situation + facts
        text = " ".join([body.situation] + body.facts)
        keywords = [w for w in text.split() if len(w) >= 4][:8]
        if vs is not None:
            try:
                raw = vs.keyword_search_cases(keywords=keywords, limit=body.limit)
            except Exception as exc:
                logger.warning("Keyword search cases failed: %s. Using demo fallback.", exc)
                raw = []
        if not raw:
            search_mode = "demo_fallback"
            raw = _ranked_fallback(
                [item for item in _FALLBACK_CASES if domain == "general" or item.get("law_type") == domain] or _FALLBACK_CASES,
                text,
                ["title", "situation_summary", "outcome", "lesson", "law_type"],
                body.limit,
            )

    # Step 3: build response items
    items: list[SimilarCaseItem] = []
    for c in raw[: body.limit]:
        c_domain = c.get("law_type", domain)
        c_stage = c.get("stage", stage)
        score = float(c.get("vector_score", 0.5))
        items.append(
            SimilarCaseItem(
                case_id=c.get("case_id", ""),
                title=c.get("title", ""),
                situation_summary=c.get("situation_summary", ""),
                outcome=c.get("outcome", c.get("result", "")),
                lesson=c.get("lesson", ""),
                domain=c_domain,
                domain_label=_DOMAIN_LABELS.get(c_domain, c_domain),
                key_laws=c.get("key_laws", []),
                similarity_score=round(score, 3),
                similarity_label=_similarity_label(score),
                stage=c_stage,
                stage_label=_STAGE_LABELS.get(c_stage, c_stage),
            )
        )

    # Step 4: summary
    count = len(items)
    if count == 0:
        summary = "Không tìm thấy vụ việc tương tự. Thử mô tả chi tiết hơn hoặc cung cấp thêm sự kiện."
    elif count == 1:
        summary = f"Tìm thấy 1 vụ việc tương tự trong lĩnh vực {_DOMAIN_LABELS.get(domain, domain)}."
    else:
        top_score = items[0].similarity_score
        summary = (
            f"Tìm thấy {count} vụ việc tương tự trong lĩnh vực "
            f"{_DOMAIN_LABELS.get(domain, domain)}. "
            f"Vụ việc gần nhất có độ tương đồng {round(top_score * 100)}%."
        )

    return SimilarCasesResponse(
        request_id="sim_" + str(uuid.uuid4())[:8],
        query_domain=domain,
        query_domain_label=_DOMAIN_LABELS.get(domain, domain),
        query_stage=stage,
        query_stage_label=_STAGE_LABELS.get(stage, stage),
        similar_cases=items,
        total=count,
        search_mode=search_mode,
        summary=summary,
    )


# ── Clause similarity search models ──────────────────────────────────────────


class ClauseSearchRequest(BaseModel):
    clause_text: str = Field(..., min_length=5)
    clause_type: Optional[str] = None
    risk_level: Optional[str] = None
    limit: int = Field(default=6, ge=1, le=20)


class ClauseItem(BaseModel):
    clause_id: str
    doc_id: str
    clause_text: str
    clause_type: str
    risk_level: str
    risk_label: str
    similarity_score: float
    similarity_label: str
    suggestion: str


class ClauseSearchResponse(BaseModel):
    request_id: str
    feature: str = "clause_similarity"
    query: str
    results: List[ClauseItem]
    total: int
    search_mode: str
    summary: str


_RISK_LABELS: dict[str, str] = {
    "critical": "Rất rủi ro",
    "high":     "Rủi ro cao",
    "medium":   "Rủi ro trung bình",
    "low":      "Ít rủi ro",
    "safe":     "An toàn",
}

_CLAUSE_TYPE_LABELS: dict[str, str] = {
    "termination":          "Điều khoản chấm dứt",
    "penalty":              "Điều khoản phạt",
    "confidentiality":      "Điều khoản bảo mật",
    "intellectual_property": "Sở hữu trí tuệ",
    "force_majeure":        "Bất khả kháng",
    "dispute_resolution":   "Giải quyết tranh chấp",
    "payment":              "Điều khoản thanh toán",
    "scope":                "Phạm vi công việc",
    "duration":             "Thời hạn hợp đồng",
    "employment":           "Điều khoản lao động",
    "general":              "Điều khoản chung",
}


@retrieval_router.post("/clauses", response_model=ClauseSearchResponse)
def search_similar_clauses(
    body: ClauseSearchRequest,
    request: Request,
    user_id: str = Depends(require_user),
) -> ClauseSearchResponse:
    """
    Tìm kiếm điều khoản hợp đồng tương tự.
    Embed clause đầu vào, vector search trong contract_clauses (fallback: keyword).
    """
    vs = _get_vector_storage(request)

    search_mode = "vector"
    try:
        from src.pipeline.embedding_stage import embed_text
        embedding = embed_text(body.clause_text)
    except Exception:
        embedding = None

    raw: list = []
    if embedding and vs is not None:
        try:
            raw = vs.vector_search_similar_clauses(
                query_vector=embedding,
                clause_type=body.clause_type or None,
                risk_level=body.risk_level or None,
                limit=body.limit,
            )
            # Fallback: drop filters if too few results
            if len(raw) < 2 and (body.clause_type or body.risk_level):
                raw = vs.vector_search_similar_clauses(
                    query_vector=embedding,
                    limit=body.limit,
                )
        except Exception as e:
            logger.warning("Vector search similar clauses failed: %s. Falling back to keyword search.", e)
            raw = []

    if not embedding or not raw:
        search_mode = "keyword"
        keywords = [w for w in body.clause_text.split() if len(w) >= 3][:8]
        # Keyword fallback using chunks with clause content matching
        raw_chunks = []
        if vs is not None:
            try:
                raw_chunks = vs.keyword_search_chunks(keywords=keywords, filter_user_id=user_id, limit=body.limit)
            except Exception as exc:
                logger.warning("Keyword search clauses failed: %s. Using demo fallback.", exc)
        # Wrap chunks as clause-like items
        raw = [
            {
                "clause_id": c.get("chunk_id", ""),
                "doc_id": c.get("doc_id", ""),
                "clause_text": c.get("content", ""),
                "clause_type": "general",
                "risk_level": "medium",
                "suggestion": "",
                "vector_score": c.get("vector_score", 0.4),
            }
            for c in raw_chunks
        ]
        if not raw:
            search_mode = "demo_fallback"
            raw = _ranked_fallback(
                _FALLBACK_CLAUSES,
                body.clause_text,
                ["clause_text", "clause_type", "suggestion"],
                body.limit,
            )

    items: list[ClauseItem] = []
    for c in raw[: body.limit]:
        score = float(c.get("vector_score", 0.5))
        c_type = c.get("clause_type", "general")
        risk = c.get("risk_level", "medium")
        items.append(ClauseItem(
            clause_id=c.get("clause_id", c.get("chunk_id", "")),
            doc_id=c.get("doc_id", ""),
            clause_text=c.get("clause_text", c.get("content", ""))[:500],
            clause_type=c_type,
            risk_level=risk,
            risk_label=_RISK_LABELS.get(risk, risk),
            similarity_score=round(score, 3),
            similarity_label=_similarity_label(score),
            suggestion=c.get("suggestion", ""),
        ))

    count = len(items)
    summary = (
        f"Tìm thấy {count} điều khoản tương tự."
        if count else
        "Không tìm thấy điều khoản tương tự trong cơ sở dữ liệu. Hãy tải lên thêm hợp đồng để so sánh."
    )

    return ClauseSearchResponse(
        request_id="cls_" + str(uuid.uuid4())[:8],
        query=body.clause_text[:120],
        results=items,
        total=count,
        search_mode=search_mode,
        summary=summary,
    )
