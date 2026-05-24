#!/usr/bin/env python3
"""Query lka.db directly to diagnose file_uploads and chunks."""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "lka.db"
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

print(f"DB: {DB}  ({DB.stat().st_size // 1024} KB)\n")

# file_uploads
rows = conn.execute("SELECT doc_id, file_path FROM file_uploads").fetchall()
print(f"=== file_uploads ({len(rows)} rows) ===")
for r in rows:
    exists = "EXISTS" if Path(r["file_path"]).exists() else "MISSING"
    print(f"  [{exists}]  {r['doc_id'][:12]}  {r['file_path']}")

# documents
print()
docs = conn.execute("SELECT doc_id, filename, status, is_global FROM documents ORDER BY filename").fetchall()
print(f"=== documents ({len(docs)} rows) ===")
for d in docs:
    has_fp = any(r["doc_id"] == d["doc_id"] for r in rows)
    flag = "" if has_fp else "  <-- NO file_path!"
    print(f"  {d['filename']:<45} {d['status']:^8} global={d['is_global']}{flag}")

# jobs
print()
jobs = conn.execute("SELECT doc_id, status, error FROM jobs ORDER BY created_at DESC").fetchall()
print(f"=== jobs ({len(jobs)} rows) — last 20 ===")
for j in list(jobs)[:20]:
    err = (j["error"] or "")[:80]
    print(f"  {j['doc_id'][:12]}  {j['status']:<10}  {err}")
