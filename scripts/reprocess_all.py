#!/usr/bin/env python3
"""
Direct reprocessing of all zero-chunk documents — no backend required.
Runs PipelineOrchestrator + embed_chunks_into_mongo directly for each doc.
"""
from __future__ import annotations
import os, sys, logging
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

import sqlite3
from pymongo import MongoClient

SEP = "=" * 70

# ── Connect to SQLite and MongoDB ─────────────────────────────────────────────
conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
mongo_db = MongoClient(uri)[db_name]

# ── Find all zero-chunk docs ──────────────────────────────────────────────────
chunk_counts = defaultdict(int)
for c in mongo_db.chunks_vec.find({}, {"doc_id": 1}):
    chunk_counts[c.get("doc_id", "")] += 1

docs = conn.execute(
    "SELECT doc_id, filename, user_id, status, is_global FROM documents WHERE status='ready'"
).fetchall()
file_map = {r["doc_id"]: r["file_path"] for r in conn.execute(
    "SELECT doc_id, file_path FROM file_uploads"
).fetchall()}

zero_docs = [
    d for d in docs
    if chunk_counts.get(d["doc_id"], 0) == 0
    and d["filename"].endswith((".doc", ".docx", ".pdf", ".html"))
    and file_map.get(d["doc_id"])
    and Path(file_map[d["doc_id"]]).exists()
]

print(SEP)
print(f"REPROCESS ALL ZERO-CHUNK DOCS ({len(zero_docs)} found)")
print(SEP)
for d in zero_docs:
    print(f"  {d['filename']}")

if not zero_docs:
    print("Nothing to reprocess!")
    sys.exit(0)

# ── Verify MongoDB reachable ──────────────────────────────────────────────────
from src.mongodb.client import ping as mongo_ping
if not mongo_ping():
    print("ERROR: MongoDB unreachable. Check MONGO_URI in .env")
    sys.exit(1)
print(f"\nMongoDB: OK")

# ── Load models once ──────────────────────────────────────────────────────────
from src.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.embedding_stage import embed_chunks_into_mongo
from src.mongodb.mongo_storage import VectorStorage

print("Loading embedding model (first doc may be slow)...")
config      = PipelineConfig()
vec_storage = VectorStorage()

# ── Process each doc ──────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("PROCESSING")
print(SEP)

results = []
for idx, doc in enumerate(zero_docs, 1):
    doc_id   = doc["doc_id"]
    filename = doc["filename"]
    user_id  = doc["user_id"]
    is_global = bool(doc["is_global"]) or user_id == "admin"
    file_path = Path(file_map[doc_id])

    safe_name = filename.encode("ascii", "replace").decode("ascii")
    print(f"\n[{idx}/{len(zero_docs)}] {safe_name}")

    try:
        orch   = PipelineOrchestrator(config)
        result = orch.run(file_path)

        if orch.last_chunk_set is None or not orch.last_chunk_set.chunks:
            print(f"  SKIP: pipeline produced 0 chunks (status={result.overall_status})")
            results.append((filename, 0, "no_chunks"))
            continue

        chunk_count = len(orch.last_chunk_set.chunks)
        doc_family = ""
        doc_type = ""
        last_doc = getattr(orch, "last_document", None)
        if last_doc is not None:
            meta = getattr(last_doc, "metadata", None)
            if meta is not None:
                doc_family = getattr(meta, "document_family", "") or ""
                doc_type = getattr(meta, "document_type", "") or ""

        stored = embed_chunks_into_mongo(
            orch.last_chunk_set, doc_id, user_id, vec_storage, is_global=is_global,
            document_family=doc_family,
            document_type=doc_type,
        )
        print(f"  OK: {chunk_count} chunks produced, {stored} stored in MongoDB")
        results.append((filename, stored, "ok"))

    except Exception as exc:
        print(f"  ERROR: {type(exc).__name__}: {str(exc)[:120]}")
        results.append((filename, 0, f"error: {exc}"))

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("SUMMARY")
print(SEP)

ok_count    = sum(1 for _, _, s in results if s == "ok")
skip_count  = sum(1 for _, _, s in results if s == "no_chunks")
error_count = sum(1 for _, _, s in results if s.startswith("error"))
total_stored = sum(n for _, n, s in results if s == "ok")

print(f"  Processed  : {len(results)}")
print(f"  OK         : {ok_count}  ({total_stored} total chunks stored)")
print(f"  No chunks  : {skip_count}")
print(f"  Errors     : {error_count}")

if error_count or skip_count:
    print("\nDetails:")
    for fname, n, status in results:
        if status != "ok":
            safe = fname.encode("ascii", "replace").decode("ascii")
            print(f"  {safe}: {status}")

# ── Final MongoDB count ───────────────────────────────────────────────────────
total_after = mongo_db.chunks_vec.count_documents({})
docs_after  = len(set(
    c["doc_id"] for c in mongo_db.chunks_vec.find({}, {"doc_id": 1})
))
print(f"\nMongoDB chunks_vec total : {total_after}")
print(f"Unique doc_ids with chunks: {docs_after}")
