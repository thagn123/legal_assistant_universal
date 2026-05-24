#!/usr/bin/env python3
"""Inspect MongoDB chunks_vec directly and trace where chunks actually land."""
from __future__ import annotations
import os, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

import requests
from pymongo import MongoClient

API     = os.environ.get("API_URL", "http://localhost:8001")
KEY     = os.environ.get("ADMIN_API_KEY", "lexai-admin-secret")
HEADERS = {"X-Admin-Key": KEY}
uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
db      = MongoClient(uri)[db_name]

SEP = "=" * 70

# ── 1. All chunks in MongoDB ───────────────────────────────────────────────────
chunks = list(db.chunks_vec.find({}, {"doc_id": 1, "user_id": 1, "is_global": 1}))
print(SEP)
print(f"ALL CHUNKS IN MONGODB: {len(chunks)}")
print(SEP)
doc_id_counts = Counter(c.get("doc_id", "?") for c in chunks)
for did, cnt in sorted(doc_id_counts.items(), key=lambda x: -x[1]):
    print(f"  {cnt:4d} chunks  doc_id={did}")

# ── 2. All doc_ids from admin API ─────────────────────────────────────────────
print(f"\n{SEP}")
print("ALL DOC_IDs IN ADMIN API")
print(SEP)
r = requests.get(f"{API}/admin/documents", headers=HEADERS, params={"limit": 200}, timeout=30)
docs = r.json()
if isinstance(docs, dict):
    docs = docs.get("documents", [])

api_doc_ids = {d.get("doc_id"): d.get("filename") for d in docs}
for did, fname in sorted(api_doc_ids.items(), key=lambda x: x[1] or ""):
    in_mongo = doc_id_counts.get(did, 0)
    mark = "OK" if in_mongo > 0 else "MISSING"
    print(f"  [{mark}]  {fname:<45} doc_id={did[:12]}  chunks={in_mongo}")

# ── 3. Check reprocess endpoint behavior ─────────────────────────────────────
print(f"\n{SEP}")
print("REPROCESS ENDPOINT CHECK (one doc)")
print(SEP)
zero_docs = [
    d for d in docs
    if doc_id_counts.get(d.get("doc_id", ""), 0) == 0
    and d.get("status") == "ready"
]
if zero_docs:
    test = zero_docs[0]
    doc_id = test.get("doc_id", "")
    fname  = test.get("filename", "")
    print(f"  Testing reprocess for: {fname}  ({doc_id[:12]})")
    r = requests.post(
        f"{API}/admin/documents/{doc_id}/reprocess",
        headers=HEADERS, timeout=30
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body  : {r.text[:300]}")

# ── 4. Check reprocess code ───────────────────────────────────────────────────
print(f"\n{SEP}")
print("CHECKING REPROCESS ENDPOINT SOURCE")
print(SEP)
# Look at the admin_routes reprocess handler
admin_routes = ROOT / "src" / "api" / "admin_routes.py"
text = admin_routes.read_text(encoding="utf-8")
# Find the reprocess handler
idx = text.find("reprocess")
if idx != -1:
    snippet = text[max(0, idx-100):idx+500]
    print(snippet)

# ── 5. Check if file_path is registered in SQLite ────────────────────────────
print(f"\n{SEP}")
print("FILE PATH CHECK FOR ZERO-CHUNK DOCS")
print(SEP)
sys.path.insert(0, str(ROOT))
from src.runtime.storage import StorageLayer
storage = StorageLayer()
for d in zero_docs[:5]:
    doc_id = d.get("doc_id", "")
    fname  = d.get("filename", "")
    fp     = storage.get_file_path(doc_id)
    print(f"  {fname:<45}  file_path={fp}")
