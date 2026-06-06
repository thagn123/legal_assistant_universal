import sqlite3
from pathlib import Path
from src.mongodb.client import get_db

DB = Path(__file__).parent.parent / "data" / "lka.db"
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

db = get_db()
chunks_col = db["chunks_vec"]

pipeline = [
    {"$group": {
        "_id": "$doc_id",
        "law_type": {"$first": "$law_type"},
        "sample_content": {"$first": "$content"},
        "count": {"$sum": 1}
    }}
]

mongo_docs = {}
for r in chunks_col.aggregate(pipeline):
    mongo_docs[r["_id"]] = {
        "law_type": r["law_type"],
        "count": r["count"],
        "sample": r["sample_content"][:120].replace("\n", " ")
    }

sqlite_docs = conn.execute("SELECT doc_id, filename, is_global, status, metadata_json FROM documents").fetchall()

with open("inspect_doc_types_results.txt", "w", encoding="utf-8") as f:
    f.write("=== MongoDB chunks_vec Doc Types ===\n")
    f.write(f"Found {len(sqlite_docs)} documents in SQLite:\n")
    for d in sqlite_docs:
        doc_id = d["doc_id"]
        filename = d["filename"]
        is_global = d["is_global"]
        
        m_info = mongo_docs.get(doc_id)
        if m_info:
            f.write(f"Doc ID: {doc_id[:8]}... | Filename: {filename:<40} | SQLite global={is_global} | Mongo law_type={m_info['law_type']} | Chunks={m_info['count']}\n")
            f.write(f"  Sample Content: {m_info['sample']}\n\n")
        else:
            f.write(f"Doc ID: {doc_id[:8]}... | Filename: {filename:<40} | SQLite global={is_global} | NOT found in MongoDB chunks_vec!\n\n")
