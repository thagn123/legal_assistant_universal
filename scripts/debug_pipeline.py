#!/usr/bin/env python3
"""
Pipeline debug + auto-reprocess:
1. Show all docs with 0 MongoDB chunks
2. Check SQLite for saved chunk_sets
3. Reprocess all zero-chunk docs via POST /admin/documents/{id}/reprocess
4. Poll until done, then show final chunk counts
"""
from __future__ import annotations
import os, sys, time, logging
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.ERROR)

import requests
from pymongo import MongoClient

API     = os.environ.get("API_URL", "http://localhost:8001")
KEY     = os.environ.get("ADMIN_API_KEY", "lexai-admin-secret")
HEADERS = {"X-Admin-Key": KEY}
uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
db      = MongoClient(uri)[db_name]

SEP = "=" * 70

# ── 1. Get all docs and MongoDB chunk counts ──────────────────────────────────
r = requests.get(f"{API}/admin/documents", headers=HEADERS, params={"limit": 200}, timeout=30)
docs = r.json()
if isinstance(docs, dict):
    docs = docs.get("documents", [])

chunk_counts = defaultdict(int)
for c in db.chunks_vec.find({}, {"doc_id": 1}):
    chunk_counts[c.get("doc_id", "")] += 1

zero_docs = [
    d for d in docs
    if chunk_counts.get(d.get("doc_id", ""), 0) == 0
    and d.get("status") == "ready"
    and d.get("filename", "").endswith((".doc", ".docx", ".pdf", ".html"))
]

print(SEP)
print("STEP 1 -- DOCUMENTS WITH 0 MONGODB CHUNKS")
print(SEP)
print(f"  {'FILENAME':<45} {'CHUNKS':^7}")
print("  " + "-" * 55)
for doc in sorted(docs, key=lambda d: d.get("filename", "")):
    doc_id = doc.get("doc_id", "")
    fname  = doc.get("filename", "")[:44]
    cnt    = chunk_counts.get(doc_id, 0)
    status = doc.get("status", "?")
    flag   = " <-- ZERO" if cnt == 0 and status == "ready" else ""
    print(f"  {fname:<44} {cnt:^7}{flag}")

print(f"\n  {len(zero_docs)} docs need reprocessing")

# ── 2. Check if SQLite has chunk_sets for these docs ─────────────────────────
print(f"\n{SEP}")
print("STEP 2 -- SQLITE CHUNK_SET CHECK")
print(SEP)
from src.runtime.storage import StorageLayer
storage = StorageLayer()

sqlite_has_chunks = 0
for doc in zero_docs:
    doc_id = doc.get("doc_id", "")
    cs = storage.load_chunk_set_json(doc_id)
    if cs:
        sqlite_has_chunks += 1
        print(f"  SQLite HAS chunks: {doc.get('filename','?')} ({len(cs)} bytes json)")
    else:
        print(f"  SQLite EMPTY:      {doc.get('filename','?')}")

print(f"\n  SQLite chunk_sets found: {sqlite_has_chunks} / {len(zero_docs)}")

# ── 3. Reprocess all zero-chunk docs ─────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 3 -- REPROCESSING ZERO-CHUNK DOCS")
print(SEP)

reprocess_doc_ids = []
for doc in zero_docs:
    doc_id = doc.get("doc_id", "")
    fname  = doc.get("filename", "?")
    r = requests.post(
        f"{API}/admin/documents/{doc_id}/reprocess",
        headers=HEADERS,
        timeout=30,
    )
    if r.status_code in (200, 201, 202):
        print(f"  queued: {fname}")
        reprocess_doc_ids.append(doc_id)
    else:
        print(f"  ERROR {r.status_code}: {fname} -- {r.text[:100]}")

print(f"\n  {len(reprocess_doc_ids)} jobs queued")

if not reprocess_doc_ids:
    print("Nothing to reprocess.")
    sys.exit(0)

# ── 4. Poll until all complete ────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 4 -- WAITING FOR JOBS TO COMPLETE (max 15 min)")
print(SEP)

terminal  = {"complete", "failed"}
max_wait  = 900   # 15 min
poll_s    = 8
deadline  = time.monotonic() + max_wait
statuses  = {d: "queued" for d in reprocess_doc_ids}

while time.monotonic() < deadline:
    time.sleep(poll_s)
    r = requests.get(f"{API}/admin/jobs", headers=HEADERS, params={"limit": 500}, timeout=30)
    jobs = r.json()
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", [])
    for j in jobs:
        did = j.get("doc_id", "")
        if did in statuses:
            statuses[did] = j.get("status", "unknown")
    pending = [d for d, s in statuses.items() if s not in terminal]
    done    = len(statuses) - len(pending)
    failed  = sum(1 for s in statuses.values() if s == "failed")
    print(f"  {done}/{len(statuses)} done  |  {len(pending)} running  |  {failed} failed")
    if not pending:
        break
else:
    print("  WARNING: timeout — some jobs still running")

# ── 5. Final chunk count ──────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 5 -- FINAL MONGODB CHUNK COUNTS")
print(SEP)

chunk_counts2 = defaultdict(int)
for c in db.chunks_vec.find({}, {"doc_id": 1}):
    chunk_counts2[c.get("doc_id", "")] += 1

total_chunks = sum(chunk_counts2.values())
docs_with_chunks = sum(1 for v in chunk_counts2.values() if v > 0)

r2 = requests.get(f"{API}/admin/documents", headers=HEADERS, params={"limit": 200}, timeout=30)
docs2 = r2.json()
if isinstance(docs2, dict):
    docs2 = docs2.get("documents", [])

print(f"  {'FILENAME':<45} {'CHUNKS':^7}")
print("  " + "-" * 55)
for doc in sorted(docs2, key=lambda d: d.get("filename", "")):
    doc_id = doc.get("doc_id", "")
    fname  = doc.get("filename", "")[:44]
    cnt    = chunk_counts2.get(doc_id, 0)
    status = doc.get("status", "?")
    flag   = " *** NEW ***" if doc_id in reprocess_doc_ids and cnt > 0 else (" <-- 0!" if cnt == 0 and status == "ready" else "")
    print(f"  {fname:<44} {cnt:^7}{flag}")

print(f"\n  Total MongoDB chunks : {total_chunks}")
print(f"  Docs with chunks     : {docs_with_chunks}")

failed_reprocess = [did for did, s in statuses.items() if s == "failed"]
if failed_reprocess:
    print(f"\n  Failed ({len(failed_reprocess)}):")
    for did in failed_reprocess:
        r3 = requests.get(f"{API}/admin/jobs", headers=HEADERS, params={"limit": 500}, timeout=30)
        jobs3 = r3.json()
        if isinstance(jobs3, dict): jobs3 = jobs3.get("jobs", [])
        for j in jobs3:
            if j.get("doc_id") == did and j.get("status") == "failed":
                print(f"    {did[:12]}  error: {j.get('error','?')[:120]}")
                break
