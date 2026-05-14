"""
Multilingual retrieval layer for the Legal GraphRAG system.

Modules:
  legal_aliases        — Vietnamese/English/canonical term mapping table
  language_detector    — language detection with jurisdiction and confidence
  query_normalizer     — normalize "Article 1", "Điều 1", "Art. 1" → article_1
  canonical_references — generate and match canonical legal IDs
  retrieval_engine     — keyword-based multilingual retrieval over ChunkSet
"""
