"""
Unit tests for Phase 24 Task 3.1 — document domain-aware adaptive chunking.
Tests _detect_law_type() and _choose_chunk_strategy() with different document metadata and keywords.
"""

from __future__ import annotations

from src.config import ChunkingStrategy
from src.schemas.document import CanonicalDocument, DocumentMetadata, DocumentProfile, Block, Article
from src.pipeline.chunker import _choose_chunk_strategy, _detect_law_type


def test_detect_law_types():
    # Test dat_dai keyword detection
    doc = CanonicalDocument(
        document_id="test_doc",
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Quyết định về việc quản lý đất đai và cấp giấy chứng nhận quyền sử dụng đất.")],
        pages=[]
    )
    assert _detect_law_type(doc) == "dat_dai"

    # Test hop_dong keyword detection
    doc = CanonicalDocument(
        document_id="test_doc",
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Hợp đồng mua bán hàng hóa và các thỏa thuận bên mua bên bán.")],
        pages=[]
    )
    assert _detect_law_type(doc) == "hop_dong"


def test_choose_chunk_strategy_bieu_mau():
    profile = DocumentProfile(page_count=5, has_tables=False)
    doc = CanonicalDocument(
        document_id="test_doc",
        metadata=DocumentMetadata(document_family="bieu_mau"),
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Mẫu số 01 đăng ký")],
        pages=[]
    )
    strategy = _choose_chunk_strategy(profile, doc)
    assert strategy == ChunkingStrategy.MIXED_GROUP


def test_choose_chunk_strategy_hop_dong():
    # Contract with no tables -> legal_aware
    profile = DocumentProfile(page_count=10, has_tables=False, table_density=0.0)
    doc = CanonicalDocument(
        document_id="test_doc",
        metadata=DocumentMetadata(document_family="hop_dong"),
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Hợp đồng dịch vụ")],
        pages=[]
    )
    strategy = _choose_chunk_strategy(profile, doc)
    assert strategy == ChunkingStrategy.LEGAL_AWARE

    # Contract with tables -> table_aware
    profile = DocumentProfile(page_count=10, has_tables=True, table_density=0.1)
    doc = CanonicalDocument(
        document_id="test_doc",
        metadata=DocumentMetadata(document_family="hop_dong"),
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Hợp đồng dịch vụ")],
        pages=[]
    )
    strategy = _choose_chunk_strategy(profile, doc)
    assert strategy == ChunkingStrategy.TABLE_AWARE


def test_choose_chunk_strategy_dat_dai():
    profile = DocumentProfile(page_count=15, is_long_document=False)
    doc = CanonicalDocument(
        document_id="test_doc",
        metadata=DocumentMetadata(document_family="luat_phap"),
        # Has articles (structure)
        articles=[Article(article_id="art_1", label="Điều 1")],
        blocks=[Block(block_id="b1", page_id="p1", region_id="r1", block_type="paragraph", order_index=0, raw_text="Luật Đất đai năm 2024 quy định về thu hồi đất.")],
        pages=[]
    )
    strategy = _choose_chunk_strategy(profile, doc)
    assert strategy == ChunkingStrategy.STRUCTURAL
