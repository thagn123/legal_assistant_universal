#!/usr/bin/env python3
"""
Force-reprocess ALL ready documents through the updated pipeline.
Deletes old MongoDB chunks before reinserting so stale chunk_ids don't accumulate.
Use after pipeline code changes (structurer, chunker, graph_builder) to rebuild
both the SQLite graphs table and MongoDB chunks_vec with fresh data.
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

conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
mongo_db = MongoClient(uri)[db_name]

# Load all ready docs that have an existing file
docs = conn.execute(
    "SELECT doc_id, filename, user_id, status, is_global FROM documents WHERE status='ready'"
).fetchall()
file_map = {r["doc_id"]: r["file_path"] for r in conn.execute(
    "SELECT doc_id, file_path FROM file_uploads"
).fetchall()}

all_docs = [
    d for d in docs
    if d["filename"].endswith((".doc", ".docx", ".pdf", ".html"))
    and file_map.get(d["doc_id"])
    and Path(file_map[d["doc_id"]]).exists()
]

print(SEP)
print(f"FORCE REPROCESS ALL DOCS ({len(all_docs)} found)")
print(SEP)

chunk_counts = defaultdict(int)
for c in mongo_db.chunks_vec.find({}, {"doc_id": 1}):
    chunk_counts[c.get("doc_id", "")] += 1

for d in all_docs:
    safe = d["filename"].encode("ascii", "replace").decode("ascii")
    print(f"  {safe:<50} current_chunks={chunk_counts.get(d['doc_id'], 0)}")

from src.mongodb.client import ping as mongo_ping
if not mongo_ping():
    print("ERROR: MongoDB unreachable. Check MONGO_URI in .env")
    sys.exit(1)
print(f"\nMongoDB: OK")

from src.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.embedding_stage import embed_chunks_into_mongo
from src.mongodb.mongo_storage import VectorStorage
from src.runtime.storage import StorageLayer
from src.runtime.processor import _serialize_graph

storage = StorageLayer("data/lka.db")

print("Loading embedding model...")
config      = PipelineConfig()
vec_storage = VectorStorage()

print(f"\n{SEP}")
print("PROCESSING")
print(SEP)

results = []
for idx, doc in enumerate(all_docs, 1):
    doc_id    = doc["doc_id"]
    filename  = doc["filename"]
    user_id   = doc["user_id"]
    is_global = bool(doc["is_global"]) or user_id == "admin"
    file_path = Path(file_map[doc_id])

    safe_name = filename.encode("ascii", "replace").decode("ascii")
    print(f"\n[{idx}/{len(all_docs)}] {safe_name}")

    try:
        # Delete old MongoDB chunks for this doc so stale IDs don't accumulate
        deleted = vec_storage.delete_chunks_by_doc(doc_id)
        if deleted:
            print(f"  Cleared {deleted} old chunks")

        orch   = PipelineOrchestrator(config)
        result = orch.run(file_path)

        if orch.last_chunk_set is None or not orch.last_chunk_set.chunks:
            print(f"  SKIP: pipeline produced 0 chunks (status={result.overall_status})")
            results.append((filename, 0, "no_chunks"))
            continue

        chunk_count = len(orch.last_chunk_set.chunks)
        # Count citations found in the new pipeline run
        total_citations = sum(
            len(getattr(c, 'citations', []) or [])
            for c in orch.last_chunk_set.chunks
        )
        # Count chunks with hierarchy_path set
        with_hier = sum(
            1 for c in orch.last_chunk_set.chunks
            if getattr(c, 'hierarchy_path', '')
        )
        with_refs = sum(
            1 for c in orch.last_chunk_set.chunks
            if getattr(c, 'canonical_refs', [])
        )

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

        # Save graph to SQLite (pipeline builds it but doesn't persist it)
        graph_edges = 0
        if orch.last_graph is not None:
            g_json = _serialize_graph(orch.last_graph)
            storage.save_graph(doc_id, g_json)
            graph_edges = orch.last_graph.edge_count()

        print(f"  OK: {chunk_count} chunks | hier={with_hier} | canonical_refs={with_refs} | citations={total_citations} | stored={stored} | graph_edges={graph_edges}")
        results.append((filename, stored, "ok"))

    except Exception as exc:
        print(f"  ERROR: {type(exc).__name__}: {str(exc)[:120]}")
        results.append((filename, 0, f"error: {exc}"))

print(f"\n{SEP}")
print("SUMMARY")
print(SEP)

ok_count     = sum(1 for _, _, s in results if s == "ok")
skip_count   = sum(1 for _, _, s in results if s == "no_chunks")
error_count  = sum(1 for _, _, s in results if s.startswith("error"))
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

total_after = mongo_db.chunks_vec.count_documents({})
docs_after  = len(set(c["doc_id"] for c in mongo_db.chunks_vec.find({}, {"doc_id": 1})))
print(f"\nMongoDB chunks_vec total : {total_after}")
print(f"Unique doc_ids with chunks: {docs_after}")
print(f"\nNext step: python scripts/eval_graphrag.py")
