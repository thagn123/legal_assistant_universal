from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.api.deps import require_user
from src.services.situation_classifier import SituationClassifier

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
    vs = getattr(request.app.state, "vector_storage", None)
    if vs is None:
        from src.mongodb.mongo_storage import VectorStorage
        vs = VectorStorage()
    return vs


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

    if embedding:
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
    else:
        search_mode = "keyword"
        keywords = [w for w in body.query.split() if len(w) >= 3][:8]
        raw = vs.keyword_search_chunks(keywords=keywords, filter_user_id=user_id, limit=body.limit)

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

    if embedding:
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
    else:
        search_mode = "keyword"
        # Extract meaningful keywords from situation + facts
        text = " ".join([body.situation] + body.facts)
        keywords = [w for w in text.split() if len(w) >= 4][:8]
        raw = vs.keyword_search_cases(keywords=keywords, limit=body.limit)

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
    if embedding:
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
    else:
        search_mode = "keyword"
        keywords = [w for w in body.clause_text.split() if len(w) >= 3][:8]
        # Keyword fallback using chunks with clause content matching
        raw_chunks = vs.keyword_search_chunks(keywords=keywords, filter_user_id=user_id, limit=body.limit)
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
