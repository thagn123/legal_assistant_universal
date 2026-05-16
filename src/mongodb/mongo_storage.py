"""
MongoDB-backed vector storage for the Legal Knowledge Recommendation Engine.

Collections (all in the 'legal_knowledge_assistant' database):
  chunks_vec       — law article chunks with 384-dim sentence embeddings
  interactions     — user behaviour log (views, queries, situation analyses)
  templates        — pre-seeded contract templates with embeddings
  risks            — pre-seeded legal risk patterns with embeddings
  checklists       — pre-seeded compliance checklists (rule-based)
  legal_cases      — [NEW] similar legal case descriptions with embeddings
  contract_clauses — [NEW] extracted contract clauses with risk analysis

Primary DB role:
  All recommendation and vector-search operations go through MongoDB.
  Document metadata / jobs continue to live in SQLite (existing pipeline).

Indexes created on first use:
  Regular: chunks_vec(chunk_id), chunks_vec(doc_id, user_id),
           interactions(user_id, timestamp), interactions(doc_id),
           templates(industry, contract_type), risks(related_law_types),
           checklists(business_type, transaction_type),
           legal_cases(case_id), legal_cases(law_type),
           contract_clauses(doc_id), contract_clauses(risk_level)
  Vector search (Atlas / Atlas-Local):
    chunk_embedding_index    on chunks_vec.embedding       (384-dim, cosine)
    template_embedding_index on templates.embedding        (384-dim, cosine)
    risk_embedding_index     on risks.embedding            (384-dim, cosine)
    case_embedding_index     on legal_cases.embedding      (384-dim, cosine)
    clause_embedding_index   on contract_clauses.embedding (384-dim, cosine)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.mongodb.client import get_db

logger = logging.getLogger(__name__)

_VECTOR_DIM = 384


# ---------------------------------------------------------------------------
# VectorStorage
# ---------------------------------------------------------------------------


class VectorStorage:
    """
    Central repository for all MongoDB vector/recommendation data.
    Thread-safe: pymongo Collection objects are thread-safe.
    """

    def __init__(self) -> None:
        db = get_db()
        self.chunks = db["chunks_vec"]
        self.interactions = db["interactions"]
        self.templates = db["templates"]
        self.risks = db["risks"]
        self.checklists = db["checklists"]
        self.legal_cases = db["legal_cases"]          # NEW: similar case retrieval
        self.contract_clauses = db["contract_clauses"]  # NEW: clause analysis cache

    # ── Chunk vectors ────────────────────────────────────────────────────────

    def upsert_chunk_vector(
        self,
        chunk_id: str,
        doc_id: str,
        user_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Store/update a law chunk with its sentence embedding."""
        self.chunks.update_one(
            {"chunk_id": chunk_id},
            {
                "$set": {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "content": content,
                    "embedding": embedding,
                    "updated_at": _now(),
                    **metadata,
                }
            },
            upsert=True,
        )

    def vector_search_chunks(
        self,
        query_vector: List[float],
        filter_user_id: Optional[str] = None,
        law_type: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        MongoDB $vectorSearch over chunks_vec.embedding (cosine similarity).
        Returns chunks sorted by vector similarity descending.
        """
        pipeline: List[Dict] = [
            {
                "$vectorSearch": {
                    "index": "chunk_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit * 2,  # fetch extra for post-filter
                }
            },
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        ]

        # Post-filter on scalar fields (cannot use $match before $vectorSearch)
        post_match: Dict[str, Any] = {}
        if filter_user_id:
            post_match["user_id"] = filter_user_id
        if law_type:
            post_match["law_type"] = law_type
        if post_match:
            pipeline.append({"$match": post_match})

        pipeline += [
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "embedding": 0,  # do not return raw vectors
                }
            },
        ]

        try:
            return list(self.chunks.aggregate(pipeline))
        except Exception as exc:
            logger.warning("vector_search_chunks failed: %s", exc)
            return []

    def keyword_search_chunks(
        self,
        keywords: List[str],
        filter_user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fallback text search when embeddings are unavailable.
        Uses a simple $regex OR over chunk content.
        """
        if not keywords:
            return []
        regex_pattern = "|".join(keywords)
        query: Dict[str, Any] = {"content": {"$regex": regex_pattern, "$options": "i"}}
        if filter_user_id:
            query["user_id"] = filter_user_id
        try:
            return list(
                self.chunks.find(query, {"_id": 0, "embedding": 0}).limit(limit)
            )
        except Exception as exc:
            logger.warning("keyword_search_chunks failed: %s", exc)
            return []

    # ── Interactions ─────────────────────────────────────────────────────────

    def log_interaction(
        self,
        user_id: str,
        doc_id: str,
        action_type: str,
        context: Dict[str, Any],
        chunk_id: Optional[str] = None,
    ) -> None:
        """Record a user interaction for collaborative filtering."""
        self.interactions.insert_one(
            {
                "user_id": user_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "action_type": action_type,
                "context": context,
                "timestamp": _now(),
            }
        )

    def get_user_viewed_docs(self, user_id: str, limit: int = 50) -> List[str]:
        """Return doc_ids the user has interacted with, most recent first."""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$doc_id"}},
            {"$limit": limit},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("get_user_viewed_docs failed: %s", exc)
            return []

    def get_user_law_types(self, user_id: str) -> List[str]:
        """
        Aggregation: which legal domains (law_type) has this user interacted with most?
        Returns a ranked list of law_type strings.
        """
        pipeline = [
            {"$match": {"user_id": user_id, "context.law_type": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$context.law_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("get_user_law_types failed: %s", exc)
            return []

    def collaborative_filter_docs(
        self,
        user_viewed_doc_ids: List[str],
        current_user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        MongoDB Aggregation Pipeline — collaborative filtering:
        'Users who interacted with these docs also interacted with doc Y.'

        Pipeline:
          1. Find OTHER users who interacted with the same docs
          2. Lookup all their interactions (beyond the current user's docs)
          3. Score each new doc by how many similar users touched it
          4. Return top N, sorted by collaborative score
        """
        if not user_viewed_doc_ids:
            return []

        pipeline: List[Dict] = [
            # Step 1: find similar users
            {
                "$match": {
                    "doc_id": {"$in": user_viewed_doc_ids},
                    "user_id": {"$ne": current_user_id},
                }
            },
            {"$group": {"_id": "$user_id"}},
            # Step 2: get ALL docs those users touched
            {
                "$lookup": {
                    "from": "interactions",
                    "localField": "_id",
                    "foreignField": "user_id",
                    "as": "their_interactions",
                }
            },
            {"$unwind": "$their_interactions"},
            # Step 3: exclude docs the current user has already seen
            {
                "$match": {
                    "their_interactions.doc_id": {"$nin": user_viewed_doc_ids}
                }
            },
            # Step 4: score by co-occurrence
            {
                "$group": {
                    "_id": "$their_interactions.doc_id",
                    "collab_score": {"$sum": 1},
                    "similar_user_count": {"$addToSet": "$_id"},
                }
            },
            {"$sort": {"collab_score": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "doc_id": "$_id",
                    "collab_score": 1,
                    "similar_user_count": {"$size": "$similar_user_count"},
                }
            },
        ]
        try:
            return list(self.interactions.aggregate(pipeline))
        except Exception as exc:
            logger.warning("collaborative_filter_docs failed: %s", exc)
            return []

    def get_user_interaction_history(
        self,
        user_id: str,
        days: int = 60,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Return recent interactions for a user, sorted most-recent first."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        pipeline = [
            {"$match": {"user_id": user_id, "timestamp": {"$gte": cutoff}}},
            {"$sort": {"timestamp": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "user_id": 0}},
        ]
        try:
            return list(self.interactions.aggregate(pipeline))
        except Exception as exc:
            logger.warning("get_user_interaction_history failed: %s", exc)
            return []

    def get_user_action_frequency(self, user_id: str) -> Dict[str, int]:
        """Return a count of each action_type the user has performed."""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        try:
            return {r["_id"]: r["count"] for r in self.interactions.aggregate(pipeline)}
        except Exception as exc:
            logger.warning("get_user_action_frequency failed: %s", exc)
            return {}

    def get_user_active_hours(self, user_id: str) -> List[int]:
        """Return hours-of-day (0-23) the user is most active, ranked by frequency."""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$addFields": {
                    "hour": {
                        "$hour": {"$dateFromString": {"dateString": "$timestamp"}}
                    }
                }
            },
            {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 6},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("get_user_active_hours failed: %s", exc)
            return []

    def get_user_law_types_since(self, user_id: str, days: int = 7) -> List[str]:
        """Return distinct law_types the user interacted with in the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "timestamp": {"$gte": cutoff},
                    "context.law_type": {"$exists": True, "$ne": None},
                }
            },
            {"$group": {"_id": "$context.law_type"}},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("get_user_law_types_since failed: %s", exc)
            return []

    def get_user_action_bigrams(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Extract (action_N, action_N+1) bigrams from the user's chronological
        action sequence, ranked by co-occurrence count descending.
        """
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"timestamp": 1}},
            {"$group": {"_id": None, "actions": {"$push": "$action_type"}}},
            {
                "$project": {
                    "_id": 0,
                    "bigrams": {
                        "$map": {
                            "input": {
                                "$range": [
                                    0,
                                    {"$subtract": [{"$size": "$actions"}, 1]},
                                ]
                            },
                            "as": "i",
                            "in": {
                                "first": {"$arrayElemAt": ["$actions", "$$i"]},
                                "second": {
                                    "$arrayElemAt": [
                                        "$actions",
                                        {"$add": ["$$i", 1]},
                                    ]
                                },
                            },
                        }
                    },
                }
            },
            {"$unwind": "$bigrams"},
            {
                "$group": {
                    "_id": {
                        "first": "$bigrams.first",
                        "second": "$bigrams.second",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "first_action": "$_id.first",
                    "second_action": "$_id.second",
                    "count": 1,
                }
            },
        ]
        try:
            return list(self.interactions.aggregate(pipeline))
        except Exception as exc:
            logger.warning("get_user_action_bigrams failed: %s", exc)
            return []

    def find_peer_users(
        self,
        user_id: str,
        top_law_types: List[str],
        limit: int = 20,
    ) -> List[str]:
        """
        Return user_ids (excluding current user) whose interactions overlap
        with the given law_types, ranked by overlap count descending.
        """
        if not top_law_types:
            return []
        pipeline = [
            {
                "$match": {
                    "user_id": {"$ne": user_id},
                    "context.law_type": {"$in": top_law_types},
                }
            },
            {"$group": {"_id": "$user_id", "overlap": {"$sum": 1}}},
            {"$sort": {"overlap": -1}},
            {"$limit": limit},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("find_peer_users failed: %s", exc)
            return []

    def get_trending_content_for_peers(
        self,
        peer_user_ids: List[str],
        exclude_doc_ids: List[str],
        days: int = 14,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return documents trending among peer users in the last N days,
        excluding any the current user has already seen.
        """
        if not peer_user_ids:
            return []
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        _system_docs = [
            "__recommendation__", "__cases__", "__risk__", "__situation__"
        ]
        pipeline = [
            {
                "$match": {
                    "user_id": {"$in": peer_user_ids},
                    "timestamp": {"$gte": cutoff},
                    "doc_id": {"$nin": list(exclude_doc_ids) + _system_docs},
                }
            },
            {
                "$group": {
                    "_id": "$doc_id",
                    "peer_count": {"$addToSet": "$user_id"},
                    "law_type": {"$first": "$context.law_type"},
                    "last_accessed": {"$max": "$timestamp"},
                }
            },
            {"$addFields": {"peer_count": {"$size": "$peer_count"}}},
            {"$sort": {"peer_count": -1, "last_accessed": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "doc_id": "$_id",
                    "peer_count": 1,
                    "law_type": 1,
                    "last_accessed": 1,
                }
            },
        ]
        try:
            return list(self.interactions.aggregate(pipeline))
        except Exception as exc:
            logger.warning("get_trending_content_for_peers failed: %s", exc)
            return []

    def get_trending_law_types(self, limit: int = 5) -> List[str]:
        """
        Global Aggregation: which legal domains are most queried across all users?
        Used as a cold-start fallback.
        """
        pipeline = [
            {"$match": {"context.law_type": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$context.law_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]
        try:
            return [r["_id"] for r in self.interactions.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("get_trending_law_types failed: %s", exc)
            return []

    # ── Templates ────────────────────────────────────────────────────────────

    def upsert_template(self, template: Dict[str, Any]) -> None:
        self.templates.update_one(
            {"template_id": template["template_id"]},
            {"$set": template},
            upsert=True,
        )

    def vector_search_templates(
        self,
        query_vector: List[float],
        industry: Optional[str] = None,
        contract_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """$vectorSearch on templates.embedding."""
        pipeline: List[Dict] = [
            {
                "$vectorSearch": {
                    "index": "template_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 50,
                    "limit": limit * 3,
                }
            },
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        ]
        post: Dict[str, Any] = {}
        if industry:
            post["industry"] = industry
        if contract_type:
            post["contract_type"] = contract_type
        if post:
            pipeline.append({"$match": post})
        pipeline += [{"$limit": limit}, {"$project": {"_id": 0, "embedding": 0}}]
        try:
            return list(self.templates.aggregate(pipeline))
        except Exception as exc:
            logger.warning("vector_search_templates failed: %s", exc)
            return []

    def get_templates_by_profile(
        self,
        industry: Optional[str] = None,
        contract_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback: tag-based template lookup without vector search."""
        query: Dict[str, Any] = {}
        if industry:
            query["industry"] = {"$in": [industry, "general"]}
        if contract_type:
            query["contract_type"] = contract_type
        try:
            return list(
                self.templates.find(query, {"_id": 0, "embedding": 0}).limit(limit)
            )
        except Exception as exc:
            logger.warning("get_templates_by_profile failed: %s", exc)
            return []

    # ── Risks ────────────────────────────────────────────────────────────────

    def upsert_risk(self, risk: Dict[str, Any]) -> None:
        self.risks.update_one(
            {"risk_id": risk["risk_id"]},
            {"$set": risk},
            upsert=True,
        )

    def vector_search_risks(
        self,
        query_vector: List[float],
        severity: Optional[str] = None,
        limit: int = 6,
    ) -> List[Dict[str, Any]]:
        """$vectorSearch on risks.embedding."""
        pipeline: List[Dict] = [
            {
                "$vectorSearch": {
                    "index": "risk_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 60,
                    "limit": limit * 2,
                }
            },
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        ]
        if severity:
            pipeline.append({"$match": {"severity": severity}})
        pipeline += [{"$limit": limit}, {"$project": {"_id": 0, "embedding": 0}}]
        try:
            return list(self.risks.aggregate(pipeline))
        except Exception as exc:
            logger.warning("vector_search_risks failed: %s", exc)
            return []

    def get_risks_from_history(
        self,
        user_id: str,
        limit: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Aggregation Pipeline: infer risks from the user's interaction history.

        Logic:
          1. Aggregate which law types the user interacts with most
          2. $lookup risks whose related_law_types overlap
          3. Return top risks sorted by interaction frequency
        """
        pipeline: List[Dict] = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$context.law_type",
                    "interaction_count": {"$sum": 1},
                }
            },
            {"$sort": {"interaction_count": -1}},
            {"$limit": 5},
            {
                "$lookup": {
                    "from": "risks",
                    "localField": "_id",
                    "foreignField": "related_law_types",
                    "as": "matched_risks",
                }
            },
            {"$unwind": "$matched_risks"},
            {"$sort": {"interaction_count": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "law_type": "$_id",
                    "interaction_count": 1,
                    "risk": {
                        "risk_id": "$matched_risks.risk_id",
                        "name": "$matched_risks.name",
                        "severity": "$matched_risks.severity",
                        "description": "$matched_risks.description",
                        "indicators": "$matched_risks.indicators",
                        "related_law_types": "$matched_risks.related_law_types",
                        "mitigation": "$matched_risks.mitigation",
                    },
                }
            },
        ]
        try:
            return list(self.interactions.aggregate(pipeline))
        except Exception as exc:
            logger.warning("get_risks_from_history failed: %s", exc)
            return []

    # ── Checklists ───────────────────────────────────────────────────────────

    def upsert_checklist(self, checklist: Dict[str, Any]) -> None:
        self.checklists.update_one(
            {"checklist_id": checklist["checklist_id"]},
            {"$set": checklist},
            upsert=True,
        )

    def get_checklists(
        self,
        business_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Rule-based checklist lookup by business type and/or transaction type."""
        query: Dict[str, Any] = {}
        if business_type:
            query["$or"] = [
                {"business_type": business_type},
                {"business_type": "general"},
            ]
        if transaction_type:
            query["transaction_type"] = transaction_type
        try:
            return list(
                self.checklists.find(query, {"_id": 0}).sort("priority", 1).limit(limit)
            )
        except Exception as exc:
            logger.warning("get_checklists failed: %s", exc)
            return []

    # ── Legal Cases ───────────────────────────────────────────────────────────

    def upsert_case(self, case: Dict[str, Any]) -> None:
        """Store/update a legal case document."""
        self.legal_cases.update_one(
            {"case_id": case["case_id"]},
            {"$set": {**case, "updated_at": _now()}},
            upsert=True,
        )

    def vector_search_cases(
        self,
        query_vector: List[float],
        law_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """$vectorSearch on legal_cases.embedding for similar situations."""
        pipeline: List[Dict] = [
            {
                "$vectorSearch": {
                    "index": "case_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit * 2,
                }
            },
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        ]
        if law_type:
            pipeline.append({"$match": {"law_type": law_type}})
        pipeline += [{"$limit": limit}, {"$project": {"_id": 0, "embedding": 0}}]
        try:
            return list(self.legal_cases.aggregate(pipeline))
        except Exception as exc:
            logger.warning("vector_search_cases failed: %s", exc)
            return []

    def keyword_search_cases(
        self,
        keywords: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Keyword fallback for legal case search."""
        if not keywords:
            return []
        pattern = "|".join(keywords)
        try:
            return list(
                self.legal_cases.find(
                    {
                        "$or": [
                            {"situation_summary": {"$regex": pattern, "$options": "i"}},
                            {"title": {"$regex": pattern, "$options": "i"}},
                        ]
                    },
                    {"_id": 0, "embedding": 0},
                ).limit(limit)
            )
        except Exception as exc:
            logger.warning("keyword_search_cases failed: %s", exc)
            return []

    def get_cases_by_law_type(
        self, law_type: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return cases filtered by legal domain."""
        try:
            return list(
                self.legal_cases.find(
                    {"law_type": law_type},
                    {"_id": 0, "embedding": 0},
                ).sort("priority", 1).limit(limit)
            )
        except Exception as exc:
            logger.warning("get_cases_by_law_type failed: %s", exc)
            return []

    # ── Contract Clauses ──────────────────────────────────────────────────────

    def save_contract_analysis(
        self,
        doc_id: str,
        user_id: str,
        clauses: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> None:
        """Cache a contract clause analysis result."""
        self.contract_clauses.update_one(
            {"doc_id": doc_id},
            {
                "$set": {
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "clauses": clauses,
                    "metadata": metadata,
                    "updated_at": _now(),
                }
            },
            upsert=True,
        )

    def get_contract_analysis(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached clause analysis for a document."""
        try:
            return self.contract_clauses.find_one(
                {"doc_id": doc_id}, {"_id": 0}
            )
        except Exception as exc:
            logger.warning("get_contract_analysis failed: %s", exc)
            return None

    def vector_search_similar_clauses(
        self,
        query_vector: List[float],
        clause_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar clauses across all analyzed contracts."""
        pipeline: List[Dict] = [
            {
                "$vectorSearch": {
                    "index": "clause_embedding_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit * 2,
                }
            },
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        ]
        post: Dict[str, Any] = {}
        if clause_type:
            post["clause_type"] = clause_type
        if risk_level:
            post["risk_level"] = risk_level
        if post:
            pipeline.append({"$match": post})
        pipeline += [{"$limit": limit}, {"$project": {"_id": 0, "embedding": 0}}]
        try:
            return list(self.contract_clauses.aggregate(pipeline))
        except Exception as exc:
            logger.warning("vector_search_similar_clauses failed: %s", exc)
            return []

    # ── Index setup (run once on startup) ────────────────────────────────────

    def setup_indexes(self) -> None:
        """
        Create regular and vector-search indexes.
        Safe to call multiple times (idempotent).
        """
        # Regular indexes
        self.chunks.create_index([("chunk_id", 1)], unique=True)
        self.chunks.create_index([("doc_id", 1), ("user_id", 1)])
        self.chunks.create_index([("law_type", 1)])
        self.interactions.create_index([("user_id", 1), ("timestamp", -1)])
        self.interactions.create_index([("doc_id", 1)])
        self.interactions.create_index([("action_type", 1)])
        self.templates.create_index([("industry", 1), ("contract_type", 1)])
        self.risks.create_index([("related_law_types", 1)])
        self.risks.create_index([("severity", 1)])
        self.checklists.create_index([("business_type", 1), ("transaction_type", 1)])
        # New collections
        self.legal_cases.create_index([("case_id", 1)], unique=True)
        self.legal_cases.create_index([("law_type", 1)])
        self.legal_cases.create_index([("outcome", 1)])
        self.contract_clauses.create_index([("doc_id", 1)])
        self.contract_clauses.create_index([("user_id", 1)])
        self.contract_clauses.create_index([("risk_level", 1)])
        logger.info("Regular MongoDB indexes created.")

        # Vector search indexes (Atlas / Atlas-Local format)
        db = get_db()
        _create_vector_index(
            db,
            collection="chunks_vec",
            index_name="chunk_embedding_index",
            path="embedding",
            num_dimensions=_VECTOR_DIM,
        )
        _create_vector_index(
            db,
            collection="templates",
            index_name="template_embedding_index",
            path="embedding",
            num_dimensions=_VECTOR_DIM,
        )
        _create_vector_index(
            db,
            collection="risks",
            index_name="risk_embedding_index",
            path="embedding",
            num_dimensions=_VECTOR_DIM,
        )
        _create_vector_index(
            db,
            collection="legal_cases",
            index_name="case_embedding_index",
            path="embedding",
            num_dimensions=_VECTOR_DIM,
        )
        _create_vector_index(
            db,
            collection="contract_clauses",
            index_name="clause_embedding_index",
            path="embedding",
            num_dimensions=_VECTOR_DIM,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_vector_index(
    db,
    collection: str,
    index_name: str,
    path: str,
    num_dimensions: int,
    similarity: str = "cosine",
) -> None:
    """Create an Atlas vector search index (no-op if already exists)."""
    try:
        db.command(
            {
                "createSearchIndexes": collection,
                "indexes": [
                    {
                        "name": index_name,
                        "type": "vectorSearch",
                        "definition": {
                            "fields": [
                                {
                                    "type": "vector",
                                    "path": path,
                                    "numDimensions": num_dimensions,
                                    "similarity": similarity,
                                }
                            ]
                        },
                    }
                ],
            }
        )
        logger.info("Vector index '%s' created on collection '%s'.", index_name, collection)
    except Exception as exc:
        # Index already exists → ignore; other errors → warn
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate" in msg or "IndexAlreadyExists" in str(exc):
            logger.debug("Vector index '%s' already exists — skipping.", index_name)
        else:
            logger.warning(
                "Could not create vector index '%s' on '%s': %s",
                index_name,
                collection,
                exc,
            )
