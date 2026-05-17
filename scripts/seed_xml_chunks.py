#!/usr/bin/env python3
"""
Seed MongoDB chunks_vec directly from the VNLegalText XML corpus.

Bypasses the 8-stage pipeline — reads XML files, strips tags, splits by
article (Điều X), embeds with SentenceTransformer, upserts to MongoDB
as global chunks (is_global=True, user_id="admin").

Usage:
    python scripts/seed_xml_chunks.py
    python scripts/seed_xml_chunks.py --limit 500
    python scripts/seed_xml_chunks.py --no-embed   # text only, no vectors

Requires: MongoDB running at MONGO_URI (default localhost:27017)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_XML_DIR = (
    ROOT
    / "raw_data"
    / "VNLegalText-main"
    / "VNLegalText-main"
    / "data"
    / "xml_data"
    / "dataset"
)

_MIN_LEN = 60    # discard chunks shorter than this
_MAX_LEN = 900   # hard-truncate long chunks before embedding

# ── Law-type keyword detector ──────────────────────────────────────────────────

_DOMAIN_MAP = [
    ("dat_dai",        ["đất đai", "quyền sử dụng đất", "sổ đỏ", "sổ hồng", "bồi thường đất"]),
    ("hop_dong",       ["hợp đồng", "bên mua", "bên bán", "bên thuê", "điều khoản hợp đồng"]),
    ("lao_dong",       ["lao động", "người lao động", "hợp đồng lao động", "bảo hiểm xã hội"]),
    ("doanh_nghiep",   ["doanh nghiệp", "công ty", "cổ đông", "vốn điều lệ", "tnhh", "cổ phần"]),
    ("hinh_su",        ["tội phạm", "hình sự", "bị can", "bị cáo", "truy tố", "khởi tố"]),
    ("dan_su",         ["dân sự", "bồi thường", "tranh chấp dân sự", "thừa kế", "di chúc"]),
    ("hanh_chinh",     ["hành chính", "khiếu nại", "quyết định hành chính", "ubnd"]),
    ("gia_dinh",       ["hôn nhân", "ly hôn", "nuôi con", "cấp dưỡng"]),
    ("thuong_mai",     ["thương mại", "mua bán hàng hóa", "kinh doanh"]),
]


def _law_type(text: str) -> str:
    low = text.lower()
    for slug, kws in _DOMAIN_MAP:
        if any(k in low for k in kws):
            return slug
    return "general"


# ── Text helpers ───────────────────────────────────────────────────────────────


def _strip_tags(raw: str) -> str:
    """Remove XML/HTML-style tags; normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"[ \t]+", " ", text).strip()


def _split_articles(text: str, doc_id: str) -> list[dict]:
    """
    Split a legal document into article-level chunks.
    Primary split: 'Điều N.' markers.
    If no Điều is found, split by paragraph (≥_MIN_LEN chars).
    """
    parts = re.split(r"(?=Điều\s+\d+[\s\.\:])", text)
    chunks: list[dict] = []

    for i, part in enumerate(parts):
        part = part.strip()
        if len(part) < _MIN_LEN:
            continue

        # Long articles: break on newlines (keep meaningful paragraphs)
        if len(part) > _MAX_LEN:
            paras = [p.strip() for p in part.split("\n") if len(p.strip()) >= _MIN_LEN]
            for j, para in enumerate(paras):
                chunks.append({"id": f"{doc_id}_{i}_{j}", "text": para[:_MAX_LEN]})
        else:
            chunks.append({"id": f"{doc_id}_{i}", "text": part})

    # Fallback: whole document
    if not chunks:
        body = text.strip()[:_MAX_LEN]
        if len(body) >= _MIN_LEN:
            chunks.append({"id": f"{doc_id}_0", "text": body})

    return chunks


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed MongoDB chunks_vec from VNLegalText XML corpus."
    )
    parser.add_argument(
        "--limit", type=int, default=300,
        help="Maximum number of XML files to process (default 300).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="SentenceTransformer batch size for embedding (default 32).",
    )
    parser.add_argument(
        "--no-embed", action="store_true",
        help="Skip embedding — store text-only chunks (keyword search still works).",
    )
    args = parser.parse_args()

    # ── MongoDB connection ────────────────────────────────────────────────────
    try:
        from src.mongodb.client import ping
        from src.mongodb.mongo_storage import VectorStorage
    except ImportError as exc:
        print(f"ERROR: Cannot import src.mongodb: {exc}")
        print("Run from project root:  python scripts/seed_xml_chunks.py")
        sys.exit(1)

    if not ping():
        print("ERROR: MongoDB not reachable. Start it first (docker compose up -d).")
        sys.exit(1)

    vs = VectorStorage()
    vs.setup_indexes()
    logger.info("MongoDB connected. Existing chunks: %d", vs.chunks.count_documents({}))

    # ── Embedding model ───────────────────────────────────────────────────────
    embed_fn = None
    if not args.no_embed:
        try:
            from src.pipeline.embedding_stage import embed_batch as _embed_batch, _get_model
            if _get_model() is not None:
                embed_fn = _embed_batch
                logger.info("Embedding model ready.")
            else:
                logger.warning("Embedding model failed to load — storing text-only chunks.")
        except Exception as exc:
            logger.warning("Cannot load embedding model (%s) — text-only mode.", exc)

    # ── Discover XML files ────────────────────────────────────────────────────
    if not _XML_DIR.exists():
        print(f"ERROR: XML corpus not found at:\n  {_XML_DIR}")
        sys.exit(1)

    xml_files = sorted(_XML_DIR.glob("*.xml"))[: args.limit]
    logger.info("Processing %d XML files from %s …", len(xml_files), _XML_DIR)

    # ── Process files ─────────────────────────────────────────────────────────
    now_ts = datetime.now(timezone.utc).isoformat()
    total_files = 0
    total_chunks = 0
    stored = 0
    errors = 0

    for xml_path in xml_files:
        try:
            raw = xml_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Cannot read %s: %s", xml_path.name, exc)
            errors += 1
            continue

        doc_id = f"xml_{xml_path.stem}"
        title = raw.split("\n")[0].strip()[:120] or xml_path.stem
        body = _strip_tags(raw)
        chunks = _split_articles(body, doc_id)

        if not chunks:
            continue

        total_files += 1
        total_chunks += len(chunks)
        texts = [c["text"] for c in chunks]

        # Embed batch
        embeddings = embed_fn(texts) if embed_fn else [None] * len(chunks)

        # Upsert to MongoDB
        for chunk, emb in zip(chunks, embeddings):
            law_type = _law_type(chunk["text"])
            doc: dict = {
                "chunk_id":       chunk["id"],
                "doc_id":         doc_id,
                "user_id":        "admin",
                "content":        chunk["text"],
                "is_global":      True,
                "chunk_type":     "article",
                "law_type":       law_type,
                "canonical_refs": [],
                "language":       "vi",
                "confidence":     1.0,
                "hierarchy_path": [title],
                "source_file":    xml_path.name,
                "updated_at":     now_ts,
            }
            if emb is not None:
                doc["embedding"] = emb

            try:
                vs.chunks.update_one(
                    {"chunk_id": chunk["id"]}, {"$set": doc}, upsert=True
                )
                stored += 1
            except Exception as exc:
                logger.warning("upsert failed for %s: %s", chunk["id"], exc)
                errors += 1

        if stored % 200 == 0 and stored > 0:
            logger.info("  … %d chunks stored so far", stored)

    # ── Summary ───────────────────────────────────────────────────────────────
    final_count = vs.chunks.count_documents({})
    global_count = vs.chunks.count_documents({"is_global": True})

    print()
    print("=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)
    print(f"  Files processed : {total_files}")
    print(f"  Chunks extracted: {total_chunks}")
    print(f"  Chunks stored   : {stored}")
    print(f"  Errors          : {errors}")
    print(f"  Embedded        : {'yes' if embed_fn else 'no (text-only)'}")
    print(f"  chunks_vec total: {final_count}  (global: {global_count})")
    print("=" * 60)

    if stored == 0:
        print("\nWARNING: No chunks were stored. Check MongoDB connection and XML path.")
        sys.exit(1)


if __name__ == "__main__":
    main()
