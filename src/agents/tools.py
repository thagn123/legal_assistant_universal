"""
Tool implementations for the Legal Reasoning Agent.

Each public function corresponds to one OpenAI tool defined in
src/llm/tool_calling.py. Tools wrap the existing infrastructure
(VectorStorage, GraphRAG) and return JSON strings consumable by the LLM.

The dispatch_tool() function is the single entry point for the agent loop.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def retrieve_relevant_laws(
    query: str,
    vector_storage,
    law_type: Optional[str] = None,
    limit: int = 8,
) -> str:
    """
    MongoDB $vectorSearch for law chunks semantically matching *query*.
    Returns JSON string.
    """
    from src.pipeline.embedding_stage import embed_text

    results: List[Dict] = []
    embedding = embed_text(query)

    if embedding:
        raw = vector_storage.vector_search_chunks(
            query_vector=embedding,
            law_type=law_type,
            limit=limit,
        )
    else:
        keywords = [w for w in query.split() if len(w) > 3][:8]
        raw = vector_storage.keyword_search_chunks(keywords, limit=limit)

    for doc in raw[:limit]:
        refs = doc.get("canonical_refs", [])
        law_ref = refs[0] if refs else doc.get("law_type", "Văn bản pháp luật")
        results.append(
            {
                "chunk_id": doc.get("chunk_id", ""),
                "law_reference": law_ref,
                "content": doc.get("content", "")[:800],
                "relevance_score": round(float(doc.get("vector_score", 0.5)), 3),
                "law_type": doc.get("law_type", ""),
                "hierarchy_path": doc.get("hierarchy_path", ""),
            }
        )

    if not results:
        return json.dumps(
            {
                "found": 0,
                "message": (
                    "Không tìm thấy điều luật liên quan. "
                    "Cần upload văn bản pháp luật vào hệ thống để cải thiện kết quả."
                ),
                "laws": [],
            },
            ensure_ascii=False,
        )

    return json.dumps({"found": len(results), "laws": results}, ensure_ascii=False)


def retrieve_similar_cases(
    situation: str,
    vector_storage,
    law_type: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search the legal_cases collection for semantically similar situations.
    Returns JSON string.
    """
    from src.pipeline.embedding_stage import embed_text

    results: List[Dict] = []
    embedding = embed_text(situation)

    if embedding:
        try:
            raw = vector_storage.vector_search_cases(
                query_vector=embedding,
                law_type=law_type,
                limit=limit,
            )
            results = raw
        except Exception as exc:
            logger.warning("vector_search_cases failed: %s", exc)

    if not results:
        keywords = [w for w in situation.split() if len(w) > 3][:6]
        try:
            results = vector_storage.keyword_search_cases(keywords, limit=limit)
        except Exception:
            results = []

    if not results:
        return json.dumps(
            {
                "found": 0,
                "message": "Chưa có tình huống tương tự trong hệ thống.",
                "cases": [],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "found": len(results),
            "cases": [
                {
                    "case_id": c.get("case_id", ""),
                    "title": c.get("title", ""),
                    "situation": c.get("situation_summary", "")[:400],
                    "outcome": c.get("outcome", ""),
                    "result": c.get("result", ""),
                    "law_type": c.get("law_type", ""),
                    "key_laws": c.get("key_laws", []),
                    "similarity_score": round(float(c.get("vector_score", 0.5)), 3),
                    "lesson": c.get("lesson", ""),
                }
                for c in results[:limit]
            ],
        },
        ensure_ascii=False,
    )


def analyze_contract_risks(
    contract_text: str,
    vector_storage,
    contract_type: Optional[str] = None,
) -> str:
    """
    Find similar risk patterns from MongoDB for the contract excerpt.
    Returns JSON string with database-backed risk patterns.
    """
    from src.pipeline.embedding_stage import embed_text

    similar_risks: List[Dict] = []
    if vector_storage:
        try:
            embedding = embed_text(contract_text[:500])
            if embedding:
                raw_risks = vector_storage.vector_search_risks(
                    query_vector=embedding, limit=5
                )
                similar_risks = [
                    {
                        "risk_id": r.get("risk_id", ""),
                        "name": r.get("name", ""),
                        "description": r.get("description", ""),
                        "severity": r.get("severity", ""),
                        "indicators": r.get("indicators", [])[:3],
                        "mitigation": r.get("mitigation", [])[:2],
                    }
                    for r in raw_risks
                ]
        except Exception as exc:
            logger.warning("risk search for contract failed: %s", exc)

    return json.dumps(
        {
            "contract_type": contract_type or "unknown",
            "text_preview": contract_text[:200],
            "similar_risks_from_db": similar_risks,
            "risk_count": len(similar_risks),
        },
        ensure_ascii=False,
    )


def generate_compliance_checklist(
    vector_storage,
    business_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Retrieve compliance checklists from MongoDB by business/transaction type.
    Returns JSON string.
    """
    try:
        raw = vector_storage.get_checklists(
            business_type=business_type,
            transaction_type=transaction_type,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("get_checklists failed: %s", exc)
        raw = []

    if not raw:
        return json.dumps(
            {
                "found": 0,
                "message": "Không tìm thấy checklist phù hợp.",
                "checklists": [],
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "found": len(raw),
            "checklists": [
                {
                    "name": c.get("name", ""),
                    "business_type": c.get("business_type", ""),
                    "transaction_type": c.get("transaction_type", ""),
                    "total_items": len(c.get("items", [])),
                    "required_items": [
                        it.get("description", "")
                        for it in c.get("items", [])
                        if it.get("required", True)
                    ][:5],
                    "related_laws": c.get("related_laws", [])[:3],
                }
                for c in raw
            ],
        },
        ensure_ascii=False,
    )


def retrieve_graph_context(
    law_references: List[str],
    vector_storage,
    depth: int = 2,
) -> str:
    """
    Expand law references via the knowledge graph stored in MongoDB.
    Finds related chunks that share canonical_refs with the given laws.
    Returns JSON string.
    """
    results: List[Dict] = []

    for law_ref in law_references[:5]:
        try:
            search_term = law_ref[:30]
            related = list(
                vector_storage.chunks.find(
                    {
                        "$or": [
                            {
                                "canonical_refs": {
                                    "$regex": search_term,
                                    "$options": "i",
                                }
                            },
                            {"content": {"$regex": search_term, "$options": "i"}},
                        ]
                    },
                    {"_id": 0, "embedding": 0},
                ).limit(3)
            )
            for r in related:
                results.append(
                    {
                        "source_law": law_ref,
                        "related_chunk_id": r.get("chunk_id", ""),
                        "related_refs": r.get("canonical_refs", [])[:3],
                        "hierarchy_path": r.get("hierarchy_path", ""),
                        "content": r.get("content", "")[:300],
                    }
                )
        except Exception as exc:
            logger.warning(
                "graph context retrieval failed for %s: %s", law_ref, exc
            )

    if not results:
        return json.dumps(
            {
                "found": 0,
                "message": "Không tìm thấy ngữ cảnh graph cho các điều luật đã cho.",
                "context": [],
            },
            ensure_ascii=False,
        )

    return json.dumps({"found": len(results), "context": results}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def dispatch_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    vector_storage,
) -> str:
    """
    Single entry point: routes a tool call from the agent loop to the
    correct implementation. Returns a JSON string in all cases.
    """
    try:
        if tool_name == "retrieve_relevant_laws":
            return retrieve_relevant_laws(
                query=tool_args.get("query", ""),
                vector_storage=vector_storage,
                law_type=tool_args.get("law_type"),
                limit=int(tool_args.get("limit", 8)),
            )
        elif tool_name == "retrieve_similar_cases":
            return retrieve_similar_cases(
                situation=tool_args.get("situation", ""),
                vector_storage=vector_storage,
                law_type=tool_args.get("law_type"),
                limit=int(tool_args.get("limit", 5)),
            )
        elif tool_name == "analyze_contract_risks":
            return analyze_contract_risks(
                contract_text=tool_args.get("contract_text", ""),
                vector_storage=vector_storage,
                contract_type=tool_args.get("contract_type"),
            )
        elif tool_name == "generate_compliance_checklist":
            return generate_compliance_checklist(
                vector_storage=vector_storage,
                business_type=tool_args.get("business_type"),
                transaction_type=tool_args.get("transaction_type"),
            )
        elif tool_name == "retrieve_graph_context":
            return retrieve_graph_context(
                law_references=tool_args.get("law_references", []),
                vector_storage=vector_storage,
                depth=int(tool_args.get("depth", 2)),
            )
        else:
            return json.dumps(
                {"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False
            )
    except Exception as exc:
        logger.error("Tool dispatch error for %s: %s", tool_name, exc)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
