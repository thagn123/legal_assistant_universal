#!/usr/bin/env python3
"""
Phase B: Cross-document graph enricher.

Scans chunk content for Vietnamese amendment phrases (sửa đổi, bãi bỏ, thay thế)
that reference other laws by their official number (e.g. "Luật số 92/2015/QH13").
Writes AMENDS, INVALIDATES, and OVERRIDES edges between Document nodes in the
SQLite graphs table.

Run after force_reprocess_all.py has rebuilt all per-document graphs.
"""
from __future__ import annotations
import os, sys, re, json, uuid, logging
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

import sqlite3
from pymongo import MongoClient

SEP = "=" * 70

# ---------------------------------------------------------------------------
# Law number extraction from filenames  e.g. 92_2015_QH13_296861.doc → 92/2015/QH13
# ---------------------------------------------------------------------------
_FILENAME_LAW_RE = re.compile(r'^(\d+)_(\d{4})_(QH\d+)_', re.IGNORECASE)


def filename_to_law_key(filename: str) -> str | None:
    m = _FILENAME_LAW_RE.match(filename)
    if not m:
        return None
    num = str(int(m.group(1)))   # strip leading zeros: 01 → 1
    year = m.group(2)
    qh = m.group(3).upper()
    return f"{num}/{year}/{qh}"


# ---------------------------------------------------------------------------
# Amendment phrase detection
# Patterns (case-insensitive, simplified for Vietnamese legal text):
#   AMENDS:      "sửa đổi [,bổ sung]? ... số X/Y/QHZ"
#   INVALIDATES: "bãi bỏ ... số X/Y/QHZ"
#   OVERRIDES:   "thay thế ... số X/Y/QHZ"
# ---------------------------------------------------------------------------
_LAW_NUM_RE = re.compile(
    r'(?:số\s+)?(\d{1,3}/\d{4}/(?:QH|UBTVQH|HĐNN)\d+)',
    re.IGNORECASE,
)

_AMENDS_PHRASE_RE = re.compile(
    r'(?:sửa\s+đổi|bổ\s+sung|sửa\s+đổi,?\s+bổ\s+sung)',
    re.IGNORECASE,
)
_INVALIDATES_PHRASE_RE = re.compile(
    r'(?:bãi\s+bỏ|hủy\s+bỏ|bãi\s+bỏ\s+toàn\s+bộ)',
    re.IGNORECASE,
)
_OVERRIDES_PHRASE_RE = re.compile(
    r'(?:thay\s+thế|thay\s+cho|thay\s+bằng)',
    re.IGNORECASE,
)


def classify_amendment(window: str) -> str | None:
    """Return edge type for a text window containing a law number reference."""
    if _OVERRIDES_PHRASE_RE.search(window):
        return "OVERRIDES"
    if _INVALIDATES_PHRASE_RE.search(window):
        return "INVALIDATES"
    if _AMENDS_PHRASE_RE.search(window):
        return "AMENDS"
    return None


def extract_amendment_refs(content: str) -> list[tuple[str, str]]:
    """
    Return list of (law_number_key, edge_type) for all amendment references
    found in the content string.  Window = 200 chars before the law number.
    """
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for m in _LAW_NUM_RE.finditer(content):
        law_num_raw = m.group(1)
        # Normalize: strip leading zeros from first component
        parts = law_num_raw.split("/", 1)
        try:
            num_norm = str(int(parts[0]))
        except ValueError:
            num_norm = parts[0]
        law_key = f"{num_norm}/{parts[1].upper()}" if len(parts) == 2 else law_num_raw

        start = max(0, m.start() - 200)
        window = content[start:m.end()]
        edge_type = classify_amendment(window)
        if edge_type:
            pair = (law_key, edge_type)
            if pair not in seen:
                results.append(pair)
                seen.add(pair)
    return results


# ---------------------------------------------------------------------------
# Graph edge helper
# ---------------------------------------------------------------------------
def _make_cross_edge(from_id: str, edge_type: str, to_id: str, evidence: str) -> dict:
    return {
        "edge_id": str(uuid.uuid4()),
        "from_node_id": from_id,
        "edge_type": edge_type,
        "to_node_id": to_id,
        "confidence": 0.80,
        "provenance": {"method": "amendment_phrase_scan", "evidence": evidence[:120]},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

uri = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
mongo_db = MongoClient(uri)[db_name]

# 1. Build law_key → doc_id index from filenames
rows = conn.execute(
    "SELECT doc_id, filename FROM documents WHERE status='ready'"
).fetchall()

law_key_to_doc_ids: dict[str, list[str]] = defaultdict(list)
doc_id_to_law_key: dict[str, str] = {}

for r in rows:
    key = filename_to_law_key(r["filename"])
    if key:
        law_key_to_doc_ids[key].append(r["doc_id"])
        doc_id_to_law_key[r["doc_id"]] = key

print(SEP)
print(f"LAW NUMBER INDEX: {len(law_key_to_doc_ids)} unique law numbers across {len(rows)} docs")
for k, ids in sorted(law_key_to_doc_ids.items()):
    print(f"  {k:20s}  → doc_ids {[i[:8] for i in ids]}")
print()

# 2. Load all graphs from SQLite
graph_rows = conn.execute("SELECT doc_id, graph_json FROM graphs").fetchall()
doc_id_to_graph: dict[str, dict] = {}
doc_id_to_doc_node_id: dict[str, str] = {}   # doc_id → Document node_id in graph

for r in graph_rows:
    g = json.loads(r["graph_json"])
    doc_id = r["doc_id"]
    doc_id_to_graph[doc_id] = g
    # Find the Document node
    for node in g.get("nodes", []):
        if node.get("node_type") == "Document":
            doc_id_to_doc_node_id[doc_id] = node["node_id"]
            break

print(f"GRAPHS LOADED: {len(doc_id_to_graph)} docs with graphs")
print()

# 3. Scan MongoDB chunks for amendment references
print(SEP)
print("SCANNING CHUNKS FOR AMENDMENT PHRASES")
print(SEP)

# Get all chunks (only doc_id + content needed)
all_chunks = list(mongo_db.chunks_vec.find(
    {}, {"doc_id": 1, "content": 1}
))
print(f"Total chunks to scan: {len(all_chunks)}")

# Group by doc_id
chunks_by_doc: dict[str, list[str]] = defaultdict(list)
for c in all_chunks:
    content = c.get("content") or ""
    if content:
        chunks_by_doc[c["doc_id"]].append(content)

# 4. Find cross-doc amendment relationships
new_edges_by_src_doc: dict[str, list[dict]] = defaultdict(list)
relationship_log: list[tuple] = []

for src_doc_id, contents in chunks_by_doc.items():
    src_node_id = doc_id_to_doc_node_id.get(src_doc_id)
    if not src_node_id:
        continue

    seen_pairs: set[tuple] = set()
    for content in contents:
        refs = extract_amendment_refs(content)
        for law_key, edge_type in refs:
            # Resolve target docs
            tgt_doc_ids = law_key_to_doc_ids.get(law_key, [])
            for tgt_doc_id in tgt_doc_ids:
                if tgt_doc_id == src_doc_id:
                    continue
                tgt_node_id = doc_id_to_doc_node_id.get(tgt_doc_id)
                if not tgt_node_id:
                    continue
                pair = (src_node_id, edge_type, tgt_node_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                edge = _make_cross_edge(src_node_id, edge_type, tgt_node_id, evidence=law_key)
                new_edges_by_src_doc[src_doc_id].append(edge)
                relationship_log.append((src_doc_id, edge_type, tgt_doc_id, law_key))

print(f"\nCross-doc relationships found: {sum(len(v) for v in new_edges_by_src_doc.values())}")
print()
for src, etype, tgt, law in relationship_log:
    src_key = doc_id_to_law_key.get(src, src[:8])
    tgt_key = doc_id_to_law_key.get(tgt, tgt[:8])
    print(f"  {src_key:20s}  -{etype}->  {tgt_key:20s}  (via {law})")

# 5. Write new edges back into graph JSONs in SQLite
print(f"\n{SEP}")
print("WRITING EDGES TO GRAPHS TABLE")
print(SEP)

docs_updated = 0
for doc_id, new_edges in new_edges_by_src_doc.items():
    g = doc_id_to_graph.get(doc_id)
    if not g:
        continue

    # Append edges (dedup by pair)
    existing_pairs = {(e["from_node_id"], e["edge_type"], e["to_node_id"]) for e in g.get("edges", [])}
    added = 0
    for edge in new_edges:
        pair = (edge["from_node_id"], edge["edge_type"], edge["to_node_id"])
        if pair not in existing_pairs:
            g["edges"].append(edge)
            existing_pairs.add(pair)
            added += 1

    if added:
        conn.execute(
            "UPDATE graphs SET graph_json=? WHERE doc_id=?",
            (json.dumps(g, ensure_ascii=False), doc_id),
        )
        docs_updated += 1
        key = doc_id_to_law_key.get(doc_id, doc_id[:8])
        print(f"  {key:20s}: +{added} new cross-doc edges")

conn.commit()
print(f"\nDocs updated: {docs_updated}")

# 6. Summary
print(f"\n{SEP}")
print("SUMMARY")
print(SEP)
total_new = sum(len(v) for v in new_edges_by_src_doc.values())
by_type: dict[str, int] = defaultdict(int)
for _, etype, __, ___ in relationship_log:
    by_type[etype] += 1

print(f"  New cross-doc edges written : {total_new}")
for etype, count in sorted(by_type.items()):
    print(f"    {etype:20s}: {count}")
print(f"  Docs with new outgoing edges: {docs_updated}")

# 7. Verify
total_cites = 0
total_amends = 0
total_invalidates = 0
total_overrides = 0
for r in conn.execute("SELECT graph_json FROM graphs").fetchall():
    g = json.loads(r[0])
    for e in g.get("edges", []):
        et = e.get("edge_type", "")
        if et == "CITES":
            total_cites += 1
        elif et == "AMENDS":
            total_amends += 1
        elif et == "INVALIDATES":
            total_invalidates += 1
        elif et == "OVERRIDES":
            total_overrides += 1

print(f"\n  CITES edges (intra-doc)     : {total_cites}")
print(f"  AMENDS edges (cross-doc)    : {total_amends}")
print(f"  INVALIDATES edges (cross)   : {total_invalidates}")
print(f"  OVERRIDES edges (cross)     : {total_overrides}")
print(f"\nNext step: python scripts/eval_graphrag.py")
