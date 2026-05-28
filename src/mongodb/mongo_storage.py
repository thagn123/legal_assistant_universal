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
import math
import re
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
        self.legal_cases = db["legal_cases"]
        self.contract_clauses = db["contract_clauses"]
        self.user_profiles = db["user_profiles"]
        self.checklist_progress = db["user_checklist_progress"]

    # ── Chunk vectors ────────────────────────────────────────────────────────

    def upsert_chunk_vector(
        self,
        chunk_id: str,
        doc_id: str,
        user_id: str,
        content: str,
        embedding: Optional[List[float]],
        metadata: Dict[str, Any],
        is_global: bool = False,
    ) -> None:
        """Store/update a law chunk. Stores even when embedding is None (keyword-searchable)."""
        doc: Dict[str, Any] = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "user_id": user_id,
            "content": content,
            "is_global": is_global,
            "has_embedding": embedding is not None,
            "updated_at": _now(),
            **metadata,
        }
        if embedding is not None:
            doc["embedding"] = embedding
        self.chunks.update_one(
            {"chunk_id": chunk_id},
            {"$set": doc},
            upsert=True,
        )

    def get_chunks_by_document(
        self,
        doc_id: str,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return all chunks for a document ordered by position (embedding excluded)."""
        query: Dict[str, Any] = {"doc_id": doc_id}
        if user_id:
            query["$or"] = [{"user_id": user_id}, {"is_global": True}]
        try:
            return list(
                self.chunks.find(query, {"_id": 0, "embedding": 0})
                .sort("position", 1)
                .limit(500)
            )
        except Exception as exc:
            logger.warning("get_chunks_by_document failed for doc_id=%s: %s", doc_id, exc)
            return []

    def get_checklist_progress(self, user_id: str, checklist_id: str) -> List[str]:
        """Return the list of checked item labels for a user's checklist."""
        try:
            doc = self.checklist_progress.find_one(
                {"user_id": user_id, "checklist_id": checklist_id}, {"_id": 0}
            )
            return doc.get("checked_items", []) if doc else []
        except Exception as exc:
            logger.warning("get_checklist_progress failed: %s", exc)
            return []

    def save_checklist_progress(
        self, user_id: str, checklist_id: str, checked_items: List[str]
    ) -> None:
        """Upsert the checked items for a user's checklist."""
        try:
            self.checklist_progress.update_one(
                {"user_id": user_id, "checklist_id": checklist_id},
                {"$set": {"checked_items": checked_items, "updated_at": _now()}},
                upsert=True,
            )
        except Exception as exc:
            logger.warning("save_checklist_progress failed: %s", exc)

    def delete_chunks_by_doc(self, doc_id: str) -> int:
        """Remove all chunks for a document. Returns count deleted."""
        try:
            result = self.chunks.delete_many({"doc_id": doc_id})
            return result.deleted_count
        except Exception as exc:
            logger.warning("delete_chunks_by_doc failed for doc_id=%s: %s", doc_id, exc)
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Return collection counts for admin dashboard."""
        try:
            return {
                "chunks_total": self.chunks.count_documents({}),
                "chunks_global": self.chunks.count_documents({"is_global": True}),
                "interactions": self.interactions.count_documents({}),
                "templates": self.templates.count_documents({}),
                "risks": self.risks.count_documents({}),
                "checklists": self.checklists.count_documents({}),
                "legal_cases": self.legal_cases.count_documents({}),
                "contract_clauses": self.contract_clauses.count_documents({}),
            }
        except Exception as exc:
            logger.warning("get_stats failed: %s", exc)
            return {}

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

        # Post-filter: user's own docs OR global (admin-uploaded) docs
        post_match: Dict[str, Any] = {}
        if filter_user_id:
            post_match["$or"] = [{"user_id": filter_user_id}, {"is_global": True}]
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
        regex_pattern = "|".join(re.escape(k) for k in keywords)
        query: Dict[str, Any] = {"content": {"$regex": regex_pattern, "$options": "i"}}
        if filter_user_id:
            query["$or"] = [{"user_id": filter_user_id}, {"is_global": True}]
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
        try:
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
        except Exception as exc:
            logger.warning("log_interaction failed: %s", exc)

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

    def update_user_profile(
        self,
        user_id: str,
        domain: str,
        user_role: str = "",
        query_snippet: str = "",
    ) -> None:
        """
        Upsert user profile after each analysis turn.
        Tracks domain frequency, last role, and recent queries for behavior personalization.
        """
        if not domain or domain == "general":
            return
        try:
            self.user_profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "last_active": _now(),
                        "last_role": user_role,
                    },
                    "$inc": {f"domain_counts.{domain}": 1},
                    "$push": {
                        "recent_queries": {
                            "$each": [{"q": query_snippet[:100], "domain": domain, "ts": _now()}],
                            "$slice": -30,
                        }
                    },
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("update_user_profile failed for user_id=%s: %s", user_id, exc)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Return the user profile document (empty dict if not found)."""
        try:
            doc = self.user_profiles.find_one({"user_id": user_id}, {"_id": 0})
            return doc or {}
        except Exception as exc:
            logger.warning("get_user_profile failed: %s", exc)
            return {}

    def get_user_law_types(self, user_id: str) -> List[str]:
        """
        Returns top legal domains for a user, merging interaction history + user profile.
        """
        scores: Dict[str, float] = {}

        # Signal 1: interaction history (action_type=situation_analysis carries law_type)
        try:
            pipeline = [
                {"$match": {"user_id": user_id, "context.law_type": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": "$context.law_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]
            for r in self.interactions.aggregate(pipeline):
                scores[r["_id"]] = scores.get(r["_id"], 0) + float(r["count"])
        except Exception as exc:
            logger.warning("get_user_law_types interactions failed: %s", exc)

        # Signal 2: persisted user profile domain counts (more durable across sessions)
        try:
            profile = self.user_profiles.find_one({"user_id": user_id}, {"domain_counts": 1, "_id": 0})
            if profile:
                for domain, cnt in (profile.get("domain_counts") or {}).items():
                    scores[domain] = scores.get(domain, 0) + float(cnt) * 1.5  # profile weighted higher
        except Exception as exc:
            logger.warning("get_user_law_types profile failed: %s", exc)

        return sorted(scores, key=lambda d: scores[d], reverse=True)[:5]

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
                    "collab_score": {
                        "$sum": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$their_interactions.action_type", "download"]}, "then": 3.0},
                                    {"case": {"$eq": ["$their_interactions.action_type", "save"]}, "then": 2.0},
                                    {"case": {"$eq": ["$their_interactions.action_type", "view"]}, "then": 1.0},
                                ],
                                "default": 0.5,
                            }
                        }
                    },
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

    # ── User Profile Embeddings (User-User CF) ────────────────────────────────

    def update_user_profile_embedding(self, user_id: str) -> bool:
        """
        Compute and upsert the user's aggregate interest embedding.

        Weights interactions by type (download=3, save=2, view=1, other=0.5),
        fetches the matching chunk embeddings, and stores a weighted L2-normalised
        average in 'user_profiles' — enabling user-user CF via $vectorSearch.
        """
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "chunk_id": {"$exists": True, "$ne": None},
                }
            },
            {"$sort": {"timestamp": -1}},
            {"$limit": 100},
            {
                "$addFields": {
                    "weight": {
                        "$switch": {
                            "branches": [
                                {"case": {"$eq": ["$action_type", "download"]}, "then": 3.0},
                                {"case": {"$eq": ["$action_type", "save"]}, "then": 2.0},
                                {"case": {"$eq": ["$action_type", "view"]}, "then": 1.0},
                            ],
                            "default": 0.5,
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$chunk_id",
                    "weight": {"$max": "$weight"},
                }
            },
        ]
        try:
            chunk_weights = {
                r["_id"]: r["weight"]
                for r in self.interactions.aggregate(pipeline)
            }
            if not chunk_weights:
                return False

            chunks = list(
                self.chunks.find(
                    {"chunk_id": {"$in": list(chunk_weights.keys())}},
                    {"chunk_id": 1, "embedding": 1, "_id": 0},
                )
            )
            if not chunks:
                return False

            dim = len(chunks[0]["embedding"])
            weighted_sum = [0.0] * dim
            total_weight = 0.0
            for chunk in chunks:
                w = chunk_weights.get(chunk["chunk_id"], 1.0)
                for i, v in enumerate(chunk["embedding"]):
                    weighted_sum[i] += w * v
                total_weight += w

            if total_weight == 0:
                return False

            avg_emb = [x / total_weight for x in weighted_sum]
            norm = math.sqrt(sum(x * x for x in avg_emb))
            if norm > 0:
                avg_emb = [x / norm for x in avg_emb]

            law_types = self.get_user_law_types(user_id)
            self.user_profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "embedding": avg_emb,
                        "top_law_types": law_types[:3],
                        "interaction_count": len(chunk_weights),
                        "updated_at": _now(),
                    }
                },
                upsert=True,
            )
            return True
        except Exception as exc:
            logger.warning("update_user_profile_embedding failed: %s", exc)
            return False

    def vector_search_similar_users(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[str]:
        """
        User-User CF via $vectorSearch on user_profiles.embedding:
        find users whose aggregate interest embeddings are most similar to
        the current user. Returns user_ids sorted by cosine similarity.
        """
        profile = self.user_profiles.find_one(
            {"user_id": user_id}, {"embedding": 1, "_id": 0}
        )
        if not profile or not profile.get("embedding"):
            return []

        pipeline = [
            {
                "$vectorSearch": {
                    "index": "user_profile_embedding_index",
                    "path": "embedding",
                    "queryVector": profile["embedding"],
                    "numCandidates": limit * 5,
                    "limit": limit + 1,
                }
            },
            {"$match": {"user_id": {"$ne": user_id}}},
            {"$limit": limit},
            {"$project": {"_id": 0, "user_id": 1}},
        ]
        try:
            return [r["user_id"] for r in self.user_profiles.aggregate(pipeline)]
        except Exception as exc:
            logger.warning("vector_search_similar_users failed: %s", exc)
            return []

    def get_item_based_cf_docs(
        self,
        user_id: str,
        exclude_doc_ids: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Item-based CF via $vectorSearch:
        for each of the user's recently interacted chunks, find K nearest
        neighbours via $vectorSearch and aggregate scores across seed chunks.
        Returns docs semantically similar to what this user has read.
        """
        recent_pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "chunk_id": {"$exists": True, "$ne": None},
                }
            },
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$chunk_id", "last_action": {"$first": "$action_type"}}},
            {"$limit": 8},
        ]
        try:
            recent = list(self.interactions.aggregate(recent_pipeline))
        except Exception as exc:
            logger.warning("get_item_based_cf_docs (fetch chunks) failed: %s", exc)
            return []

        if not recent:
            return []

        chunk_ids = [r["_id"] for r in recent]
        seeds = list(
            self.chunks.find(
                {"chunk_id": {"$in": chunk_ids}},
                {"chunk_id": 1, "embedding": 1, "_id": 0},
            )
        )
        if not seeds:
            return []

        _system_ids = {"__recommendation__", "__cases__", "__risk__", "__situation__"}
        exclude_set = set(exclude_doc_ids) | _system_ids

        doc_scores: Dict[str, float] = {}
        doc_law_types: Dict[str, str] = {}

        for seed in seeds[:5]:  # cap at 5 seeds to control latency
            emb = seed.get("embedding")
            if not emb:
                continue
            try:
                neighbors = list(
                    self.chunks.aggregate([
                        {
                            "$vectorSearch": {
                                "index": "chunk_embedding_index",
                                "path": "embedding",
                                "queryVector": emb,
                                "numCandidates": limit * 6,
                                "limit": limit * 3,
                            }
                        },
                        {"$addFields": {"sim_score": {"$meta": "vectorSearchScore"}}},
                        {"$match": {"doc_id": {"$nin": list(exclude_set)}}},
                        {"$limit": limit},
                        {"$project": {"_id": 0, "doc_id": 1, "law_type": 1, "sim_score": 1}},
                    ])
                )
            except Exception as exc:
                logger.warning("get_item_based_cf_docs ($vectorSearch) failed: %s", exc)
                continue

            for c in neighbors:
                doc_id = c.get("doc_id", "")
                if not doc_id or doc_id in exclude_set:
                    continue
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + c.get("sim_score", 0.0)
                doc_law_types.setdefault(doc_id, c.get("law_type", "general"))

        if not doc_scores:
            return []

        max_score = max(doc_scores.values())
        return [
            {
                "doc_id": doc_id,
                "item_cf_score": round(score / max_score, 4),
                "law_type": doc_law_types.get(doc_id, "general"),
            }
            for doc_id, score in sorted(doc_scores.items(), key=lambda x: -x[1])[:limit]
        ]

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
        template_type: Optional[str] = None,
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
        if template_type:
            post["template_type"] = template_type
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
        template_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fallback: tag-based template lookup without vector search."""
        query: Dict[str, Any] = {}
        if industry:
            query["industry"] = {"$in": [industry, "general"]}
        if contract_type:
            query["contract_type"] = contract_type
        if template_type:
            query["template_type"] = template_type
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
        pattern = "|".join(re.escape(k) for k in keywords)
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
        self.user_profiles.create_index([("user_id", 1)], unique=True)
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
        _create_vector_index(
            db,
            collection="user_profiles",
            index_name="user_profile_embedding_index",
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
