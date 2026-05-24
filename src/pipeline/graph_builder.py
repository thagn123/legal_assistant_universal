"""
Stage 7: Graph building

Builds graph nodes and edges from the canonical document.
Conservative: structural edges first, citation edges when evidence exists,
semantic edges only with explicit evidence.
Enriches the graph with multilingual ALIAS_OF edges via the legal ontology.

Phase 7 additions:
- Clause nodes with CONTAINS edges from parent Article nodes.
- CITES edges between Article nodes when intra-document citation targets resolve.
"""

from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional

from src.pipeline.interfaces import StageContext, StageOutput
from src.pipeline.structurer import _get_canonical_id
from src.retrieval.query_normalizer import extract_refs
from src.schemas.chunk import ChunkSet
from src.schemas.document import CanonicalDocument
from src.schemas.evaluation import STATUS_FAIL, STATUS_PASS
from src.schemas.graph import GraphBuildJob, GraphEdge, GraphNode, GraphNodeProvenance, GraphSubgraph
from src.utils import trace as T
from src.graphrag.legal_ontology import add_alias_edges


# ---------------------------------------------------------------------------
# Semantic extraction patterns (Vietnamese legal text)
# ---------------------------------------------------------------------------

_OBL_RE  = re.compile(r'(?:phải|có nghĩa vụ|có trách nhiệm|bắt buộc)', re.IGNORECASE)
_COND_RE = re.compile(r'(?:nếu |trong trường hợp|trường hợp |khi )', re.IGNORECASE)
_EXC_RE  = re.compile(r'(?:trừ trường hợp|ngoại trừ|không áp dụng|trừ khi)', re.IGNORECASE)
_PEN_RE  = re.compile(r'(?:xử phạt|bị phạt|phạt tiền|phạt cảnh cáo|xử lý vi phạm)', re.IGNORECASE)
_DEFN_RE  = re.compile(r'(?:có nghĩa là|được hiểu là|được định nghĩa là|là loại|là hành vi|là việc|là tổ chức|là cá nhân)', re.IGNORECASE)
_LAW_NUM_RE = re.compile(r'(?:số\s+)?(\d{1,3}/\d{4}/(?:QH|UBTVQH|HĐNN)\d+)', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Stage 7: Graph building
# ---------------------------------------------------------------------------


def stage_graph_building(ctx: StageContext) -> StageOutput:
    """
    Build graph nodes and edges from the canonical document.

    Edge build order (from graph-builder.md):
    1. Document and structure nodes
    2. Chunk nodes
    3. Structural edges (CONTAINS, HAS_TABLE, HAS_IMAGE, DERIVED_TO_CHUNK)
    4. Citation/reference edges (CITES) — intra-document only, evidence-gated
    5. Alias edges (ALIAS_OF) via legal_ontology enricher

    Semantic edges (MENTIONS, DEFINES, etc.) are not built here — they require
    explicit evidence from a future AI-assisted semantic pass.
    """
    if not ctx.config.enable_graph_building:
        return StageOutput(
            stage_name="graph_building",
            status="skipped",
            summary="Graph building disabled by config.",
        )

    document: CanonicalDocument = ctx.get("document")
    chunk_set: ChunkSet = ctx.get("chunk_set")
    if document is None:
        return StageOutput(
            stage_name="graph_building",
            status=STATUS_FAIL,
            summary="No document in context",
            errors=["canonical_structuring must run before graph_building"],
        )

    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    job_id = str(uuid.uuid4())

    def _make_node(node_type: str, label: str, source_ref: str, attrs: Dict = {}) -> GraphNode:
        return GraphNode(
            node_id=T.make_node_id(ctx.document_id, node_type, source_ref),
            node_type=node_type,
            label=label[:120],
            document_scope=ctx.document_id,
            source_trace=GraphNodeProvenance(
                document_id=ctx.document_id,
                source_anchor=source_ref,
                extraction_method="local",
                processing_version=ctx.config.processing_version,
                created_at=T.now_iso(),
            ),
            confidence=0.90,
            attributes=attrs,
        )

    def _make_edge(
        from_id: str,
        edge_type: str,
        to_id: str,
        confidence: float = 0.9,
        method: str = "structural",
    ) -> GraphEdge:
        return GraphEdge(
            edge_id=T.make_edge_id(from_id, edge_type, to_id),
            edge_type=edge_type,
            from_node_id=from_id,
            to_node_id=to_id,
            confidence=confidence,
            provenance=ctx.document_id,
            method=method,
        )

    # ----------------------------------------------------------------
    # 1. Document root node
    # ----------------------------------------------------------------
    doc_node = _make_node("Document", document.source_filename, document.document_id)
    nodes.append(doc_node)

    # ----------------------------------------------------------------
    # 2. Section nodes
    # ----------------------------------------------------------------
    section_node_ids: Dict[str, str] = {}
    for section in document.sections:
        cid = _get_canonical_id(section.traceability)
        attrs: Dict = {}
        if cid:
            attrs["canonical_refs"] = [cid]
        n = _make_node("Section", section.label or section.section_id, section.section_id, attrs=attrs)
        nodes.append(n)
        section_node_ids[section.section_id] = n.node_id
        edges.append(_make_edge(doc_node.node_id, "CONTAINS", n.node_id))

    # ----------------------------------------------------------------
    # 3. Article nodes
    # ----------------------------------------------------------------
    article_node_ids: Dict[str, str] = {}
    canonical_to_article_node: Dict[str, str] = {}   # canonical_ref → article node_id

    for article in document.articles:
        cid = _get_canonical_id(article.traceability)
        attrs: Dict = {}
        if cid:
            attrs["canonical_refs"] = [cid]
        n = _make_node("Article", article.label or article.article_id, article.article_id, attrs=attrs)
        nodes.append(n)
        article_node_ids[article.article_id] = n.node_id
        if cid:
            canonical_to_article_node[cid] = n.node_id
        if article.parent_section_id and article.parent_section_id in section_node_ids:
            edges.append(_make_edge(section_node_ids[article.parent_section_id], "CONTAINS", n.node_id))
        else:
            edges.append(_make_edge(doc_node.node_id, "CONTAINS", n.node_id))

    # ----------------------------------------------------------------
    # 4. Clause nodes (children of Article nodes)
    # ----------------------------------------------------------------
    clause_node_ids: Dict[str, str] = {}
    for clause in document.clauses:
        n = _make_node("Clause", clause.label or clause.clause_id, clause.clause_id)
        nodes.append(n)
        clause_node_ids[clause.clause_id] = n.node_id
        if clause.parent_article_id and clause.parent_article_id in article_node_ids:
            edges.append(_make_edge(article_node_ids[clause.parent_article_id], "CONTAINS", n.node_id))
        elif clause.parent_clause_id and clause.parent_clause_id in clause_node_ids:
            edges.append(_make_edge(clause_node_ids[clause.parent_clause_id], "CONTAINS", n.node_id))
        else:
            edges.append(_make_edge(doc_node.node_id, "CONTAINS", n.node_id))

    # ----------------------------------------------------------------
    # 5. Table nodes
    # ----------------------------------------------------------------
    for table in document.tables:
        n = _make_node("Table", table.title or table.table_id, table.table_id)
        nodes.append(n)
        edges.append(_make_edge(doc_node.node_id, "HAS_TABLE", n.node_id))

    # ----------------------------------------------------------------
    # 6. Image evidence nodes
    # ----------------------------------------------------------------
    for image in document.images:
        n = _make_node("ImageEvidence", image.image_class or image.image_id, image.image_id)
        nodes.append(n)
        edges.append(_make_edge(doc_node.node_id, "HAS_IMAGE", n.node_id))

    # ----------------------------------------------------------------
    # 7. Chunk nodes — include canonical_refs in attributes
    # ----------------------------------------------------------------
    if chunk_set:
        for chunk in chunk_set.chunks:
            chunk_attrs: Dict = {"chunk_type": chunk.chunk_type}
            chunk_canonical = getattr(chunk, "canonical_refs", None) or []
            if chunk_canonical:
                chunk_attrs["canonical_refs"] = chunk_canonical
            n = _make_node("Chunk", chunk.chunk_id, chunk.chunk_id, attrs=chunk_attrs)
            n.confidence = chunk.confidence
            nodes.append(n)
            edges.append(_make_edge(doc_node.node_id, "DERIVED_TO_CHUNK", n.node_id, confidence=0.95))
            for ref in chunk_canonical:
                tgt_art = canonical_to_article_node.get(ref)
                if tgt_art:
                    edges.append(_make_edge(n.node_id, "REFERS_TO", tgt_art, confidence=0.90, method="canonical_ref_link"))

    # ----------------------------------------------------------------
    # 8. Citation edges (CITES) — intra-document, evidence-gated
    # Add a CITES edge from an article node to another article node
    # only when extract_refs(citation_str) resolves to a known node.
    # ----------------------------------------------------------------
    existing_edge_pairs = {(e.from_node_id, e.to_node_id) for e in edges}
    citation_edges_added = 0

    for article in document.articles:
        src_node_id = article_node_ids.get(article.article_id)
        if not src_node_id:
            continue
        for citation_str in article.citations:
            if not citation_str:
                continue
            for ref in extract_refs(citation_str):
                tgt_node_id = canonical_to_article_node.get(ref)
                if tgt_node_id and tgt_node_id != src_node_id:
                    pair = (src_node_id, tgt_node_id)
                    if pair not in existing_edge_pairs:
                        edges.append(_make_edge(
                            src_node_id, "CITES", tgt_node_id,
                            confidence=0.85,
                            method="citation_ref_match",
                        ))
                        existing_edge_pairs.add(pair)
                        citation_edges_added += 1

    # ----------------------------------------------------------------
    # 9. Semantic concept nodes — Obligation, Condition, Exception,
    #    Penalty (article-level) and DefinedTerm (clause-level)
    # ----------------------------------------------------------------
    block_text: Dict[str, str] = {b.block_id: b.clean_text for b in document.blocks}

    def _get_text(block_ids: List[str]) -> str:
        return " ".join(block_text[bid] for bid in block_ids if bid in block_text and block_text[bid])

    doc_law_entities: Dict[str, str] = {}
    doc_cit_nodes: Dict[str, str] = {}
    semantic_nodes_added = 0

    for article in document.articles:
        art_nid = article_node_ids.get(article.article_id)
        if not art_nid:
            continue
        label_base = article.label or article.article_id
        text = _get_text(article.block_ids)

        for cite_str in article.citations[:2]:
            if cite_str and len(cite_str) <= 120:
                cite_key = cite_str[:50]
                if cite_key not in doc_cit_nodes:
                    cit_n = _make_node("Citation", cite_str[:80], f"cit_{cite_key}")
                    nodes.append(cit_n)
                    doc_cit_nodes[cite_key] = cit_n.node_id
                edges.append(_make_edge(art_nid, "REFERS_TO", doc_cit_nodes[cite_key], confidence=0.85, method="citation_node"))
                semantic_nodes_added += 1

        if not text:
            continue

        if _OBL_RE.search(text):
            n = _make_node("Obligation", f"NV {label_base}", f"obl_{article.article_id}")
            nodes.append(n)
            edges.append(_make_edge(art_nid, "IMPOSES", n.node_id, confidence=0.75, method="regex_semantic"))
            semantic_nodes_added += 1

        if _COND_RE.search(text):
            n = _make_node("Condition", f"DK {label_base}", f"cond_{article.article_id}")
            nodes.append(n)
            edges.append(_make_edge(art_nid, "QUALIFIED_BY", n.node_id, confidence=0.70, method="regex_semantic"))
            semantic_nodes_added += 1

        if _EXC_RE.search(text):
            n = _make_node("Exception", f"NL {label_base}", f"exc_{article.article_id}")
            nodes.append(n)
            edges.append(_make_edge(art_nid, "EXCEPTED_BY", n.node_id, confidence=0.70, method="regex_semantic"))
            semantic_nodes_added += 1

        if _PEN_RE.search(text):
            n = _make_node("Penalty", f"CT {label_base}", f"pen_{article.article_id}")
            nodes.append(n)
            edges.append(_make_edge(art_nid, "ENFORCED_BY", n.node_id, confidence=0.75, method="regex_semantic"))
            semantic_nodes_added += 1

        if _DEFN_RE.search(text):
            n = _make_node("DefinedTerm", f"KN {label_base}", f"dt_art_{article.article_id}")
            nodes.append(n)
            edges.append(_make_edge(art_nid, "DEFINES", n.node_id, confidence=0.75, method="regex_semantic"))
            semantic_nodes_added += 1

        for law_key in {m.group(1) for m in _LAW_NUM_RE.finditer(text)}:
            if law_key not in doc_law_entities:
                ent_n = _make_node("Entity", law_key, f"ent_{law_key[:30]}")
                nodes.append(ent_n)
                doc_law_entities[law_key] = ent_n.node_id
            edges.append(_make_edge(art_nid, "MENTIONS", doc_law_entities[law_key], confidence=0.80, method="law_ref_entity"))
            semantic_nodes_added += 1

    for clause in document.clauses:
        cl_nid = clause_node_ids.get(clause.clause_id)
        if not cl_nid:
            continue
        if clause.clause_kind == "definition":
            terms = clause.defined_terms if clause.defined_terms else [clause.label or clause.clause_id]
            for term in terms[:5]:
                if term and len(term) <= 120:
                    n = _make_node("DefinedTerm", term, f"dt_{clause.clause_id}_{term[:20]}")
                    nodes.append(n)
                    edges.append(_make_edge(cl_nid, "DEFINES", n.node_id, confidence=0.85, method="clause_kind"))
                    semantic_nodes_added += 1
        elif clause.clause_kind == "exception":
            n = _make_node("Exception", clause.label or clause.clause_id, f"exc_cl_{clause.clause_id}")
            nodes.append(n)
            edges.append(_make_edge(cl_nid, "EXCEPTED_BY", n.node_id, confidence=0.80, method="clause_kind"))
            semantic_nodes_added += 1

    # ----------------------------------------------------------------
    # 10. Enrich with multilingual ALIAS_OF edges (intra-document)
    # ----------------------------------------------------------------
    graph = GraphSubgraph(
        document_id=ctx.document_id,
        nodes=nodes,
        edges=edges,
    )
    graph = add_alias_edges(graph)

    graph.build_job = GraphBuildJob(
        job_id=job_id,
        document_id=ctx.document_id,
        processing_version=ctx.config.processing_version,
        created_nodes=[n.node_id for n in graph.nodes],
        created_edges=[e.edge_id for e in graph.edges],
        validation_status="passed",
        nodes_by_type=graph_nodes_by_type(graph.nodes),
        edges_by_type=graph_edges_by_type(graph.edges),
    )
    ctx.put("graph", graph)

    alias_edge_count = sum(1 for e in graph.edges if e.edge_type == "ALIAS_OF")
    ctx.logger.info(
        f"Graph built: {graph.node_count()} nodes, {graph.edge_count()} edges "
        f"(citation={citation_edges_added}, alias={alias_edge_count}, semantic={semantic_nodes_added})",
        stage="graph_building",
    )

    return StageOutput(
        stage_name="graph_building",
        status=STATUS_PASS,
        summary=(
            f"{graph.node_count()} nodes, {graph.edge_count()} edges "
            f"({alias_edge_count} ALIAS_OF)"
        ),
        output_summary={
            "total_nodes": graph.node_count(),
            "total_edges": graph.edge_count(),
            "alias_edges": alias_edge_count,
            "citation_edges": citation_edges_added,
            "nodes_by_type": graph.nodes_by_type(),
            "edges_by_type": graph.edges_by_type(),
            "structural_edges": graph.structural_edge_count(),
        },
    )


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def graph_nodes_by_type(nodes: List[GraphNode]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for n in nodes:
        counts[n.node_type] = counts.get(n.node_type, 0) + 1
    return counts


def graph_edges_by_type(edges: List[GraphEdge]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in edges:
        counts[e.edge_type] = counts.get(e.edge_type, 0) + 1
    return counts
