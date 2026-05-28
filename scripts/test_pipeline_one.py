#!/usr/bin/env python3
"""
Direct pipeline trace for one zero-chunk .doc file.
Runs the pipeline manually (no job runner) and checks every step:
  1. File path from SQLite
  2. PipelineOrchestrator.run() — did it fatal-fail?
  3. orch.last_chunk_set — is it None or has chunks?
  4. mongo_ping() — is MongoDB reachable?
  5. embed_chunks_into_mongo() — does it succeed?
  6. MongoDB chunks_vec — were chunks stored?
"""
from __future__ import annotations
import os, sys, json, logging
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

# Show INFO logs so we can see pipeline progress
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

SEP = "=" * 70

# ── 1. Pick a zero-chunk doc from SQLite ──────────────────────────────────────
print(SEP)
print("STEP 1 -- FIND ZERO-CHUNK DOC IN SQLITE")
print(SEP)

from src.runtime.storage import StorageLayer
storage = StorageLayer("data/lka.db")

from pymongo import MongoClient
uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
mongo_db = MongoClient(uri)[db_name]

chunk_counts = defaultdict(int)
for c in mongo_db.chunks_vec.find({}, {"doc_id": 1}):
    chunk_counts[c.get("doc_id", "")] += 1

import sqlite3
conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

docs = conn.execute("SELECT doc_id, filename, user_id, status FROM documents WHERE status='ready'").fetchall()
file_rows = conn.execute("SELECT doc_id, file_path FROM file_uploads").fetchall()
file_map = {r["doc_id"]: r["file_path"] for r in file_rows}

zero_docs = [
    d for d in docs
    if chunk_counts.get(d["doc_id"], 0) == 0
    and d["filename"].endswith((".doc", ".docx", ".pdf"))
]

print(f"Docs with 0 chunks: {len(zero_docs)}")
for d in zero_docs[:5]:
    fp = file_map.get(d["doc_id"], "MISSING")
    print(f"  {d['filename']:<45} file_path={fp}")

if not zero_docs:
    print("All docs have chunks — nothing to test!")
    sys.exit(0)

# Pick the first .doc file
target = zero_docs[0]
doc_id   = target["doc_id"]
filename = target["filename"]
user_id  = target["user_id"]
file_path_str = file_map.get(doc_id, "")

print(f"\nTesting: {filename}  ({doc_id[:12]})")
print(f"File  : {file_path_str}")
print(f"Exists: {Path(file_path_str).exists() if file_path_str else False}")

if not file_path_str or not Path(file_path_str).exists():
    print("ERROR: file missing — cannot test")
    sys.exit(1)

# ── 2. Run PipelineOrchestrator directly ─────────────────────────────────────
print(f"\n{SEP}")
print("STEP 2 -- RUN PIPELINE ORCHESTRATOR")
print(SEP)

from src.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator

config = PipelineConfig()
orch   = PipelineOrchestrator(config)

try:
    result = orch.run(Path(file_path_str))
    print(f"Pipeline finished: overall_status={result.overall_status}")
    print(f"Stage results:")
    for s in result.stage_results:
        print(f"  {s.stage:<30} {s.status}")
except Exception as exc:
    print(f"Pipeline EXCEPTION: {type(exc).__name__}: {exc}")
    sys.exit(1)

# ── 3. Check last_chunk_set ───────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 3 -- orch.last_chunk_set")
print(SEP)

if orch.last_chunk_set is None:
    print("last_chunk_set is NONE -- chunks never reached the orchestrator")
    print("This means stage_graph_building was skipped (fatal_failure=True somewhere before)")
    print("\nStage failure detail:")
    for s in result.stage_results:
        if s.status == "fail":
            print(f"  FAILED: {s.stage}")
            for e in s.errors:
                print(f"    error: {e}")
    sys.exit(1)
else:
    cs = orch.last_chunk_set
    print(f"last_chunk_set has {len(cs.chunks)} chunks")
    print(f"strategy_used: {cs.strategy_used}")
    if cs.chunks:
        try:
            sample_text = cs.chunks[0].content[:200].encode("ascii", "replace").decode("ascii")
            print(f"Sample chunk (first 200 chars): {sample_text!r}")
        except Exception:
            print("(sample chunk print skipped -- non-ASCII)")

# ── 4. mongo_ping() ───────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 4 -- mongo_ping()")
print(SEP)

from src.mongodb.client import ping as mongo_ping
ok = mongo_ping()
print(f"mongo_ping() = {ok}")
if not ok:
    print("MongoDB is UNREACHABLE -- that's why no chunks are stored!")
    print("Check MONGO_URI in .env and whether the cluster is running.")
    sys.exit(1)

# ── 5. embed_chunks_into_mongo() ─────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 5 -- embed_chunks_into_mongo()")
print(SEP)

from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_chunks_into_mongo

vec_storage = VectorStorage()
is_global   = user_id == "admin"

try:
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
    print(f"embed_chunks_into_mongo() returned: {stored}")
except Exception as exc:
    print(f"embed_chunks_into_mongo() EXCEPTION: {type(exc).__name__}: {exc}")
    import traceback; traceback.print_exc()

# ── 6. Verify MongoDB ─────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 6 -- VERIFY MONGODB chunks_vec")
print(SEP)

count_after = mongo_db.chunks_vec.count_documents({"doc_id": doc_id})
print(f"chunks_vec count for doc_id={doc_id[:12]}: {count_after}")

sample = mongo_db.chunks_vec.find_one({"doc_id": doc_id})
if sample:
    has_emb = sample.get("embedding") is not None
    print(f"Sample chunk: has_embedding={has_emb}  content_len={len(sample.get('content',''))}")
else:
    print("No chunks found in MongoDB after embed attempt -- something is wrong!")

print(f"\n{SEP}")
print("DIAGNOSIS COMPLETE")
print(SEP)
if count_after > 0:
    print(f"SUCCESS: {count_after} chunks stored for {filename}")
    print("The pipeline works. The original jobs must have failed silently.")
    print("Run: python scripts/debug_pipeline.py  to reprocess all zero-chunk docs.")
else:
    print("FAILURE: 0 chunks in MongoDB after manual embed.")
    print("Check logs above for the root cause.")
