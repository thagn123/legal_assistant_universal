#!/usr/bin/env python3
"""
Phase C2: Cross-document ALIAS_OF edge enricher.

Loads all per-document graphs from SQLite, calls add_cross_document_alias_edges()
from legal_ontology.py, then writes the symmetric ALIAS_OF edges back to SQLite.

ALIAS_OF edges link structurally equivalent nodes (same canonical_ref, same
node_type) across different documents — e.g. Article nodes with canonical_ref
'article_1' in Law A and Law B become connected, enabling cross-law traversal.

Run after force_reprocess_all.py has rebuilt all per-document graphs.
"""
from __future__ import annotations
import os, sys, json, logging
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

SEP = "=" * 70

conn = sqlite3.connect("data/lka.db")
conn.row_factory = sqlite3.Row

# ---------------------------------------------------------------------------
# 1. Load all graphs from SQLite
# ---------------------------------------------------------------------------
graph_rows = conn.execute("SELECT doc_id, graph_json FROM graphs").fetchall()

print(SEP)
print(f"CROSS-DOC ALIAS_OF ENRICHER")
print(SEP)
print(f"Graphs loaded: {len(graph_rows)}")

if len(graph_rows) < 2:
    print("Need at least 2 graphs. Run force_reprocess_all.py first.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# 2. Reconstruct GraphSubgraph objects from JSON
# ---------------------------------------------------------------------------
from src.schemas.graph import GraphSubgraph, GraphNode, GraphEdge, GraphNodeProvenance

def _node_from_dict(d: dict) -> GraphNode:
    prov_d = d.get("source_trace") or {}
    prov = GraphNodeProvenance(
        document_id=prov_d.get("document_id", ""),
        source_anchor=prov_d.get("source_anchor", ""),
        extraction_method=prov_d.get("extraction_method", "local"),
        processing_version=prov_d.get("processing_version", ""),
        created_at=prov_d.get("created_at", ""),
    )
    return GraphNode(
        node_id=d["node_id"],
        node_type=d["node_type"],
        label=d.get("label", ""),
        document_scope=d.get("document_scope", ""),
        source_trace=prov,
        confidence=d.get("confidence", 0.9),
        attributes=d.get("attributes") or {},
    )


def _edge_from_dict(d: dict) -> GraphEdge:
    return GraphEdge(
        edge_id=d["edge_id"],
        edge_type=d["edge_type"],
        from_node_id=d["from_node_id"],
        to_node_id=d["to_node_id"],
        confidence=d.get("confidence", 0.9),
        provenance=str(d.get("provenance", "")),
        method=d.get("method", ""),
    )


graphs: list[GraphSubgraph] = []
doc_ids: list[str] = []

for row in graph_rows:
    doc_id = row["doc_id"]
    g_dict = json.loads(row["graph_json"])
    nodes = [_node_from_dict(n) for n in g_dict.get("nodes", [])]
    edges = [_edge_from_dict(e) for e in g_dict.get("edges", [])]
    g = GraphSubgraph(document_id=doc_id, nodes=nodes, edges=edges)
    graphs.append(g)
    doc_ids.append(doc_id)

print(f"Total nodes across all graphs : {sum(g.node_count() for g in graphs):,}")
print(f"Total edges before enrichment : {sum(g.edge_count() for g in graphs):,}")
print()

# ---------------------------------------------------------------------------
# 3. Run cross-document ALIAS_OF enricher
# ---------------------------------------------------------------------------
from src.graphrag.legal_ontology import add_cross_document_alias_edges

counts = add_cross_document_alias_edges(graphs)

total_added = sum(counts.values())
print(f"ALIAS_OF edges added (total)  : {total_added:,}")
print()

# Distribution by node type
by_type: dict[str, int] = defaultdict(int)
for g in graphs:
    for e in g.edges:
        if e.edge_type == "ALIAS_OF":
            # find from_node type
            node_map = {n.node_id: n.node_type for n in g.nodes}
            nt = node_map.get(e.from_node_id, "?")
            by_type[nt] += 1

print("ALIAS_OF edges by source node type:")
for nt, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {nt:20s}: {cnt:,}")
print()

# ---------------------------------------------------------------------------
# 4. Write updated graphs back to SQLite
# ---------------------------------------------------------------------------
print(SEP)
print("WRITING UPDATED GRAPHS TO SQLITE")
print(SEP)

docs_updated = 0
for g, doc_id in zip(graphs, doc_ids):
    added = counts.get(doc_id, 0)
    if added == 0:
        continue
    # Serialize graph back to JSON
    nodes_dicts = []
    for n in g.nodes:
        nodes_dicts.append({
            "node_id": n.node_id,
            "node_type": n.node_type,
            "label": n.label,
            "document_scope": n.document_scope,
            "source_trace": {
                "document_id": n.source_trace.document_id,
                "source_anchor": n.source_trace.source_anchor,
                "extraction_method": n.source_trace.extraction_method,
                "processing_version": n.source_trace.processing_version,
                "created_at": n.source_trace.created_at,
            },
            "confidence": n.confidence,
            "attributes": n.attributes,
        })
    edges_dicts = []
    for e in g.edges:
        edges_dicts.append({
            "edge_id": e.edge_id,
            "edge_type": e.edge_type,
            "from_node_id": e.from_node_id,
            "to_node_id": e.to_node_id,
            "confidence": e.confidence,
            "provenance": e.provenance,
            "method": e.method,
        })
    g_json = json.dumps({"document_id": doc_id, "nodes": nodes_dicts, "edges": edges_dicts}, ensure_ascii=False)
    conn.execute("UPDATE graphs SET graph_json=? WHERE doc_id=?", (g_json, doc_id))
    docs_updated += 1
    print(f"  {doc_id[:8]}: +{added} ALIAS_OF edges")

conn.commit()
print(f"\nDocs updated: {docs_updated}")

# ---------------------------------------------------------------------------
# 5. Verify totals
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("VERIFICATION")
print(SEP)

total_alias = 0
total_edges_after = 0
for row in conn.execute("SELECT graph_json FROM graphs").fetchall():
    g_dict = json.loads(row[0])
    for e in g_dict.get("edges", []):
        total_edges_after += 1
        if e.get("edge_type") == "ALIAS_OF":
            total_alias += 1

print(f"Total edges in SQLite (all docs) : {total_edges_after:,}")
print(f"ALIAS_OF edges                   : {total_alias:,}")
print(f"\nNext step: python scripts/eval_graphrag.py")
