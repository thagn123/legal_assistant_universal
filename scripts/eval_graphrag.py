#!/usr/bin/env python3
"""
GraphRAG + Data Structure Quality Evaluation
Scores 10 dimensions across graph schema, semantic depth, and retrieval readiness.
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv; load_dotenv()

import sqlite3
from pymongo import MongoClient

SEP  = "=" * 65
SEP2 = "-" * 65

uri     = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
mdb     = MongoClient(uri)[db_name]

conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

# ── Load all graphs from SQLite ───────────────────────────────────────────────
graph_rows = conn.execute("SELECT doc_id, graph_json FROM graphs").fetchall()
all_nodes, all_edges = [], []
node_type_ctr  = Counter()
edge_type_ctr  = Counter()
docs_with_cites = 0
docs_with_alias = 0
cross_doc_pairs = set()

for row in graph_rows:
    raw = row["graph_json"]
    if not raw:
        continue
    try:
        data  = json.loads(raw)
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        for n in nodes:
            node_type_ctr[n.get("node_type", "?")] += 1
        for e in edges:
            et = e.get("edge_type", "?")
            edge_type_ctr[et] += 1
        if any(e.get("edge_type") == "CITES"   for e in edges): docs_with_cites += 1
        if any(e.get("edge_type") == "ALIAS_OF" for e in edges): docs_with_alias += 1
    except Exception:
        continue

n_docs  = len(graph_rows)
n_nodes = len(all_nodes)
n_edges = len(all_edges)

# Defined schema sizes
SCHEMA_NODE_TYPES = {
    "Document", "DocumentVersion", "Section", "Article", "Clause",
    "Table", "TableRow", "ImageEvidence", "Chunk", "DefinedTerm",
    "Entity", "LegalConcept", "Citation", "Obligation", "Condition",
    "Exception", "Penalty",
}
SCHEMA_EDGE_TYPES = {
    "CONTAINS", "PRECEDES", "HAS_TABLE", "HAS_IMAGE", "DERIVED_TO_CHUNK",
    "MENTIONS", "DEFINES", "REFERS_TO", "CITES", "RESOLVES_TO",
    "APPLIES_TO", "IMPOSES", "QUALIFIED_BY", "EXCEPTED_BY", "ENFORCED_BY",
    "SUPPORTS", "CONTRADICTS", "AMENDS", "OVERRIDES", "INVALIDATES",
    "CONFLICTS_WITH", "REQUIRES", "DEPENDS_ON", "ALIAS_OF",
}
CROSS_DOC_EDGE_TYPES = {"AMENDS", "OVERRIDES", "INVALIDATES", "CONFLICTS_WITH", "REQUIRES", "ALIAS_OF"}
SEMANTIC_EDGE_TYPES  = {"MENTIONS", "DEFINES", "APPLIES_TO", "IMPOSES", "QUALIFIED_BY",
                        "EXCEPTED_BY", "ENFORCED_BY", "SUPPORTS", "CONTRADICTS"}
SEMANTIC_NODE_TYPES  = {"DefinedTerm", "Entity", "LegalConcept", "Citation", "Obligation",
                        "Condition", "Exception", "Penalty"}

used_node_types = set(node_type_ctr.keys())
used_edge_types = set(edge_type_ctr.keys())

node_type_pct = 100 * len(used_node_types & SCHEMA_NODE_TYPES) / len(SCHEMA_NODE_TYPES)
edge_type_pct = 100 * len(used_edge_types & SCHEMA_EDGE_TYPES) / len(SCHEMA_EDGE_TYPES)

cross_doc_edges  = sum(edge_type_ctr.get(et, 0) for et in CROSS_DOC_EDGE_TYPES)
semantic_edges   = sum(edge_type_ctr.get(et, 0) for et in SEMANTIC_EDGE_TYPES)
semantic_nodes   = sum(node_type_ctr.get(nt, 0) for nt in SEMANTIC_NODE_TYPES)
cites_edges      = edge_type_ctr.get("CITES", 0)
alias_edges      = edge_type_ctr.get("ALIAS_OF", 0)
structural_edges = edge_type_ctr.get("CONTAINS", 0) + edge_type_ctr.get("DERIVED_TO_CHUNK", 0)

# Graph density (avg edges/node, excluding simple trees = 1.0)
density = n_edges / max(1, n_nodes)

# ── Load chunks from MongoDB ───────────────────────────────────────────────────
chunks = list(mdb.chunks_vec.find({}, {
    "hierarchy_path": 1, "chunk_type": 1, "metadata": 1,
    "doc_id": 1, "canonical_refs": 1,
}))
n_chunks = len(chunks)

def _has_hierarchy(c):
    v = c.get("hierarchy_path")
    if not v:
        return False
    if isinstance(v, list):
        return len(v) > 0
    return bool(str(v).strip())

def _has_canonical(c):
    meta = c.get("metadata") or {}
    refs = meta.get("canonical_refs") or c.get("canonical_refs") or []
    return len(refs) > 0

def _has_chunk_type(c):
    meta = c.get("metadata") or {}
    ct = meta.get("chunk_type") or c.get("chunk_type")
    return ct and ct not in ("unknown", "", None)

chunks_with_hierarchy  = sum(1 for c in chunks if _has_hierarchy(c))
chunks_with_canonical  = sum(1 for c in chunks if _has_canonical(c))
chunks_with_chunk_type = sum(1 for c in chunks if _has_chunk_type(c))

hier_pct      = 100 * chunks_with_hierarchy  / max(1, n_chunks)
canonical_pct = 100 * chunks_with_canonical  / max(1, n_chunks)
chunk_type_pct = 100 * chunks_with_chunk_type / max(1, n_chunks)

# ── Print full report ─────────────────────────────────────────────────────────
print(SEP)
print("GRAPHRAG + DATA STRUCTURE EVALUATION REPORT")
print(SEP)

print("\n[A] GRAPH OVERVIEW")
print(f"  Documents with graphs : {n_docs}")
print(f"  Total nodes           : {n_nodes:,}")
print(f"  Total edges           : {n_edges:,}")
print(f"  Avg nodes / document  : {n_nodes // max(1, n_docs)}")
print(f"  Avg edges / node      : {density:.2f}  (1.0 = pure tree, >2 = rich graph)")

print("\n[B] NODE TYPE COVERAGE  (used / defined)")
print(f"  Used: {sorted(used_node_types)}")
print(f"  Missing: {sorted(SCHEMA_NODE_TYPES - used_node_types)}")
print(f"  Coverage: {len(used_node_types & SCHEMA_NODE_TYPES)}/{len(SCHEMA_NODE_TYPES)}  ({node_type_pct:.0f}%)")
print(f"  Semantic concept nodes: {semantic_nodes}  ({sorted(used_node_types & SEMANTIC_NODE_TYPES) or 'NONE'})")

print("\n[C] EDGE TYPE COVERAGE  (used / defined)")
print(f"  Used: {sorted(used_edge_types)}")
print(f"  Missing: {sorted(SCHEMA_EDGE_TYPES - used_edge_types)}")
print(f"  Coverage: {len(used_edge_types & SCHEMA_EDGE_TYPES)}/{len(SCHEMA_EDGE_TYPES)}  ({edge_type_pct:.0f}%)")

print("\n[D] EDGE BREAKDOWN BY FAMILY")
print(f"  Structural (CONTAINS + DERIVED_TO_CHUNK) : {structural_edges:,}  ({100*structural_edges/max(1,n_edges):.0f}%)")
print(f"  Citation   (CITES, REFERS_TO, RESOLVES_TO): {cites_edges:,}")
print(f"  Semantic   (MENTIONS, DEFINES, IMPOSES...): {semantic_edges:,}")
print(f"  Cross-doc  (AMENDS, OVERRIDES, ALIAS_OF..) : {cross_doc_edges:,}")
print(f"  Docs with CITES edges   : {docs_with_cites}")
print(f"  Docs with ALIAS_OF edges: {docs_with_alias}")

print("\n[E] CHUNK METADATA QUALITY  (in chunks_vec)")
print(f"  Total chunks             : {n_chunks:,}")
print(f"  With hierarchy_path      : {chunks_with_hierarchy:,}  ({hier_pct:.0f}%)")
print(f"  With canonical_refs      : {chunks_with_canonical:,}  ({canonical_pct:.0f}%)")
print(f"  With meaningful chunk_type: {chunks_with_chunk_type:,}  ({chunk_type_pct:.0f}%)")

# ── Score each dimension ───────────────────────────────────────────────────────
print(f"\n{SEP}")
print("SCORING (100 pts total)")
print(SEP)

score = 0
details = []

# D1 Node type coverage (10 pts)
d1 = len(used_node_types & SCHEMA_NODE_TYPES)  # 5
if d1 >= 12:   s1, l1 = 10, "Excellent"
elif d1 >= 8:  s1, l1 =  7, "Good"
elif d1 >= 5:  s1, l1 =  4, "Fair"
elif d1 >= 3:  s1, l1 =  2, "Poor"
else:           s1, l1 =  0, "Critical"
score += s1
details.append(f"  [D1] Node type coverage   {d1}/{len(SCHEMA_NODE_TYPES)} types           -> {s1}/10  [{l1}]")

# D2 Edge type coverage (10 pts)
d2 = len(used_edge_types & SCHEMA_EDGE_TYPES)  # 2
if d2 >= 12:   s2, l2 = 10, "Excellent"
elif d2 >= 8:  s2, l2 =  7, "Good"
elif d2 >= 5:  s2, l2 =  4, "Fair"
elif d2 >= 3:  s2, l2 =  2, "Poor"
else:           s2, l2 =  0, "Critical"
score += s2
details.append(f"  [D2] Edge type coverage   {d2}/{len(SCHEMA_EDGE_TYPES)} types           -> {s2}/10  [{l2}]")

# D3 Cross-document legal edges (15 pts) — most critical for legal AI
if cross_doc_edges >= 50:   s3, l3 = 15, "Excellent"
elif cross_doc_edges >= 20: s3, l3 = 10, "Good"
elif cross_doc_edges >= 5:  s3, l3 =  5, "Fair"
elif cross_doc_edges >= 1:  s3, l3 =  2, "Poor"
else:                        s3, l3 =  0, "Critical"
score += s3
details.append(f"  [D3] Cross-doc edges      {cross_doc_edges} (AMENDS/OVERRIDES/ALIAS_OF)  -> {s3}/15  [{l3}]")

# D4 Intra-doc citation edges (10 pts)
if cites_edges >= 100:  s4, l4 = 10, "Excellent"
elif cites_edges >= 30: s4, l4 =  7, "Good"
elif cites_edges >= 5:  s4, l4 =  4, "Fair"
elif cites_edges >= 1:  s4, l4 =  2, "Poor"
else:                    s4, l4 =  0, "Critical"
score += s4
details.append(f"  [D4] Citation edges       {cites_edges} CITES (intra-doc)          -> {s4}/10  [{l4}]")

# D5 Semantic concept nodes (10 pts)
if semantic_nodes >= 200:  s5, l5 = 10, "Excellent"
elif semantic_nodes >= 50: s5, l5 =  7, "Good"
elif semantic_nodes >= 10: s5, l5 =  4, "Fair"
elif semantic_nodes >= 1:  s5, l5 =  2, "Poor"
else:                       s5, l5 =  0, "Critical"
score += s5
details.append(f"  [D5] Semantic concept nodes {semantic_nodes} (Obligation/Term/Entity) -> {s5}/10  [{l5}]")

# D6 Hierarchy path coverage in chunks (15 pts)
if hier_pct >= 80:   s6, l6 = 15, "Excellent"
elif hier_pct >= 50: s6, l6 = 10, "Good"
elif hier_pct >= 20: s6, l6 =  5, "Fair"
elif hier_pct >= 5:  s6, l6 =  2, "Poor"
else:                 s6, l6 =  0, "Critical"
score += s6
details.append(f"  [D6] Chunk hierarchy_path {hier_pct:.0f}% of chunks              -> {s6}/15  [{l6}]")

# D7 Canonical refs in chunk metadata (10 pts)
if canonical_pct >= 70:   s7, l7 = 10, "Excellent"
elif canonical_pct >= 40: s7, l7 =  7, "Good"
elif canonical_pct >= 15: s7, l7 =  4, "Fair"
elif canonical_pct >= 5:  s7, l7 =  2, "Poor"
else:                      s7, l7 =  0, "Critical"
score += s7
details.append(f"  [D7] Canonical refs       {canonical_pct:.0f}% of chunks              -> {s7}/10  [{l7}]")

# D8 Graph density (10 pts) — >1.5 edges/node indicates real cross-refs
if density >= 3.0:   s8, l8 = 10, "Excellent"
elif density >= 2.0: s8, l8 =  7, "Good"
elif density >= 1.5: s8, l8 =  4, "Fair"
elif density >= 1.1: s8, l8 =  2, "Poor"
else:                 s8, l8 =  0, "Critical"  # pure tree
score += s8
details.append(f"  [D8] Graph density        {density:.2f} edges/node               -> {s8}/10  [{l8}]")

# D9 Structural completeness (10 pts)
struct_types = used_node_types & {"Document", "Section", "Article", "Clause", "Chunk"}
if len(struct_types) >= 5:  s9, l9 = 10, "Excellent"
elif len(struct_types) >= 4: s9, l9 =  7, "Good"
elif len(struct_types) >= 3: s9, l9 =  4, "Fair"
else:                         s9, l9 =  2, "Poor"
score += s9
details.append(f"  [D9] Structural nodes     {sorted(struct_types)}           -> {s9}/10  [{l9}]")

print(f"\n{'DIMENSION':<55} {'SCORE':>6}")
print(SEP2)
for d in details:
    print(d)
print(SEP2)

grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"
print(f"\n  OVERALL SCORE : {score}/100  (Grade {grade})")

print(f"\n{SEP}")
print("ROOT CAUSES + PRIORITY FIXES")
print(SEP)

issues = []
if cross_doc_edges == 0:
    issues.append(("CRITICAL", "D3", "Zero cross-document edges",
        "No AMENDS/OVERRIDES/CONFLICTS_WITH between laws. This is the core value\n"
        "  of legal GraphRAG — Law A amends Article X of Law B. Needs:\n"
        "  (a) Parse law numbers from document headers\n"
        "  (b) Build a cross-doc enricher pass after all docs are loaded\n"
        "  (c) Use VNLegalText-main citation annotations as ground truth"))
if cites_edges == 0:
    issues.append(("CRITICAL", "D4", "Zero CITES edges (intra-doc)",
        "article.citations is always empty in CanonicalDocument.\n"
        "  Fix: structurer.py must populate article.citations from\n"
        "  'Theo Dieu X', 'Theo Khoan Y' patterns in article text"))
if semantic_nodes == 0:
    issues.append(("CRITICAL", "D5", "No semantic concept nodes",
        "Obligation, Condition, Exception, Penalty, DefinedTerm nodes missing.\n"
        "  Fix: Add a semantic extraction pass (regex or LLM) in graph_builder.py\n"
        "  to extract 'phai...', 'neu...thi...', 'tru truong hop...' patterns"))
if canonical_pct < 5:
    issues.append(("HIGH", "D7", "canonical_refs not reaching MongoDB chunks",
        "Retrieval fusion (Stage 3) relies on canonical_refs for graph-expanded\n"
        "  keyword search (weight 0.25). Currently providing 0 signal.\n"
        "  Fix: ensure embed_chunks_into_mongo stores chunk.canonical_refs properly"))
if hier_pct < 20:
    issues.append(("HIGH", "D6", f"hierarchy_path only {hier_pct:.0f}% coverage",
        "Paragraph-group fallback chunks (most docs) never get hierarchy_path.\n"
        "  Fix: chunker.py must set hierarchy_path even in fallback mode by\n"
        "  assigning the nearest article/section ancestor to each chunk"))
if density < 1.1:
    issues.append(("MEDIUM", "D8", "Graph is a pure containment tree",
        "Every node has exactly 1 incoming edge (CONTAINS or DERIVED_TO_CHUNK).\n"
        "  Fixing D3+D4+D5 above will naturally raise density above 1.5"))

for sev, dim, title, desc in issues:
    print(f"\n[{sev}] {dim} — {title}")
    print(f"  {desc}")

print(f"\n{SEP}")
print("UPGRADE ROADMAP (what to implement next)")
print(SEP)
roadmap = [
    ("Phase A (1-2 days)", [
        "Fix article.citations parsing in structurer.py -> CITES edges",
        "Fix canonical_refs flow into chunks_vec metadata",
        "Set hierarchy_path in chunker.py fallback mode",
    ]),
    ("Phase B (3-5 days)", [
        "Build cross-document enricher: scan law numbers from headers",
        "Match amendment/override phrases ('sua doi', 'bai bo', 'thay the')",
        "Write AMENDS/OVERRIDES/INVALIDATES edges between doc pairs",
    ]),
    ("Phase C (5-10 days)", [
        "Semantic extraction: Obligation/Condition nodes from article text",
        "DefinedTerm extraction: 'X la...' patterns -> DEFINES edges",
        "Exception nodes: 'tru truong hop...' -> EXCEPTED_BY edges",
    ]),
]
for phase, items in roadmap:
    print(f"\n  {phase}:")
    for item in items:
        print(f"    - {item}")

print()
