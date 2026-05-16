"""
Embedding stage — generates 384-dim sentence vectors for law chunks
using paraphrase-multilingual-MiniLM-L12-v2 (50 MB, supports Vietnamese).

The model is loaded lazily on first use so the rest of the pipeline
starts instantly even if sentence-transformers is not installed.

Public API:
    embed_text(text: str) -> list[float] | None
    embed_batch(texts: list[str]) -> list[list[float] | None]
    embed_chunks_into_mongo(chunk_set, doc_id, user_id, vector_storage)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

logger = logging.getLogger(__name__)

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None  # loaded lazily


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            logger.info("Loading embedding model '%s' …", _MODEL_NAME)
            _model = SentenceTransformer(_MODEL_NAME)
            logger.info("Embedding model loaded (dim=384).")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers  "
                "Vector search will fall back to keyword search."
            )
            _model = None
    return _model


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def embed_text(text: str) -> Optional[List[float]]:
    """
    Return a 384-dimensional unit-norm embedding for *text*.
    Returns None if the model is unavailable.
    """
    model = _get_model()
    if model is None:
        return None
    try:
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.tolist()
    except Exception as exc:
        logger.warning("embed_text failed: %s", exc)
        return None


def embed_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Return embeddings for a list of texts in one efficient batch.
    Elements that fail are replaced with None.
    """
    if not texts:
        return []
    model = _get_model()
    if model is None:
        return [None] * len(texts)
    try:
        vecs = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]
    except Exception as exc:
        logger.warning("embed_batch failed: %s", exc)
        return [None] * len(texts)


def embed_chunks_into_mongo(
    chunk_set,  # src.schemas.chunk.ChunkSet
    doc_id: str,
    user_id: str,
    vector_storage,  # src.mongodb.mongo_storage.VectorStorage
) -> int:
    """
    Generate embeddings for all chunks in *chunk_set* and upsert them
    into MongoDB (chunks_vec collection).

    Returns the number of chunks successfully embedded.
    Called by src.runtime.processor after the pipeline finishes.
    """
    chunks = chunk_set.chunks
    if not chunks:
        return 0

    contents = [c.content for c in chunks]
    embeddings = embed_batch(contents)

    stored = 0
    for chunk, emb in zip(chunks, embeddings):
        if emb is None:
            continue
        metadata = {
            "chunk_type": chunk.chunk_type,
            "law_type": _infer_law_type(chunk),
            "canonical_refs": chunk.canonical_refs or [],
            "language": getattr(chunk, "language", "vi"),
            "confidence": chunk.confidence,
            "hierarchy_path": getattr(chunk, "hierarchy_path", []),
        }
        vector_storage.upsert_chunk_vector(
            chunk_id=chunk.chunk_id,
            doc_id=doc_id,
            user_id=user_id,
            content=chunk.content,
            embedding=emb,
            metadata=metadata,
        )
        stored += 1

    logger.info(
        "embedding_stage: embedded %d/%d chunks for doc_id=%s",
        stored,
        len(chunks),
        doc_id,
    )
    return stored


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _infer_law_type(chunk) -> str:
    """
    Guess the legal domain from the chunk's canonical refs or content.
    Returns a short slug used for filtering recommendations.
    """
    content_lower = chunk.content.lower()
    refs = " ".join(chunk.canonical_refs or []).lower()
    combined = content_lower + " " + refs

    _KEYWORDS = [
        ("dat_dai", ["đất đai", "quyền sử dụng đất", "sổ đỏ", "sổ hồng", "giấy chứng nhận quyền"]),
        ("hop_dong", ["hợp đồng", "bên mua", "bên bán", "bên thuê", "điều khoản"]),
        ("lao_dong", ["lao động", "người lao động", "người sử dụng lao động", "hợp đồng lao động"]),
        ("doanh_nghiep", ["doanh nghiệp", "công ty", "cổ đông", "vốn điều lệ", "tnhh", "cổ phần"]),
        ("hinh_su", ["tội phạm", "hình sự", "bị can", "bị cáo", "truy tố", "khởi tố"]),
        ("dan_su", ["dân sự", "bồi thường", "tranh chấp", "nguyên đơn", "bị đơn"]),
        ("thue", ["thuế", "thu nhập", "vat", "gtgt", "khai thuế"]),
        ("so_huu_tri_tue", ["sở hữu trí tuệ", "bản quyền", "nhãn hiệu", "sáng chế", "kiểu dáng"]),
    ]

    for slug, keywords in _KEYWORDS:
        if any(kw in combined for kw in keywords):
            return slug
    return "general"
