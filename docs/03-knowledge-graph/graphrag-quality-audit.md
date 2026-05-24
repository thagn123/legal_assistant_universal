# GraphRAG & Data Structure — Quality Audit

> **Evaluated:** 2026-05-23  
> **Script:** `scripts/eval_graphrag.py`  
> **Data source:** SQLite `data/lka.db` (graphs table) + MongoDB `chunks_vec` (1,805 chunks)  
> **Overall score: 18 / 100 — Grade F**

---

## 1. Executive Summary

The current knowledge graph is a pure containment tree. Every node has exactly one incoming edge (`CONTAINS` or `DERIVED_TO_CHUNK`), no cross-document relationships exist, and zero semantic concept nodes have been extracted. The structural backbone (Document → Section → Article → Chunk) is solid, but the graph provides no legal intelligence beyond document hierarchy — it is equivalent to a glorified table of contents.

The four most critical capabilities of a legal GraphRAG system are entirely absent:

| Capability | Status |
|---|---|
| Cross-document amendment tracking (AMENDS, OVERRIDES) | 0 edges |
| Intra-document citation links (CITES) | 0 edges |
| Semantic concept nodes (Obligation, Condition, Penalty) | 0 nodes |
| Chunk provenance — hierarchy path + canonical refs | 9 % / 7 % coverage |

---

## 2. Scoring — All 9 Dimensions

| Dim | Dimension | Actual | Max | Score | Grade |
|---|---|---|---|---|---|
| D1 | Node type coverage | 5 / 17 types | 10 | **4** | Fair |
| D2 | Edge type coverage | 2 / 24 types | 10 | **0** | Critical |
| D3 | Cross-document edges | 0 (AMENDS / OVERRIDES / ALIAS_OF) | 15 | **0** | Critical |
| D4 | Intra-doc citation edges | 0 CITES | 10 | **0** | Critical |
| D5 | Semantic concept nodes | 0 (Obligation / Term / Entity) | 10 | **0** | Critical |
| D6 | Chunk `hierarchy_path` coverage | 9 % (166 / 1805) | 15 | **2** | Poor |
| D7 | Chunk `canonical_refs` coverage | 7 % (~134 / 1805) | 10 | **2** | Poor |
| D8 | Graph density | 0.99 edges / node | 10 | **0** | Critical |
| D9 | Structural node completeness | 5 / 5 types present | 10 | **10** | Excellent |
| | **TOTAL** | | **100** | **18** | **F** |

Scoring bands: A ≥ 85 · B ≥ 70 · C ≥ 55 · D ≥ 40 · F < 40

---

## 3. Raw Graph Statistics

### 3.1 SQLite `graphs` table — 29 documents

```
Total nodes  : 4,979
Total edges  : 4,950
Avg nodes/doc: 171
Avg edges/doc: 170
Density      : 0.99 edges/node  ← pure tree signature
```

**Node type breakdown:**

| Node Type | Count | % of total |
|---|---|---|
| Chunk | 2,300 | 46 % |
| Article | 2,241 | 45 % |
| Section | 408 | 8 % |
| Document | 29 | <1 % |
| Clause | 1 | <1 % |
| DefinedTerm | 0 | — |
| Entity | 0 | — |
| LegalConcept | 0 | — |
| Citation | 0 | — |
| Obligation | 0 | — |
| Condition | 0 | — |
| Exception | 0 | — |
| Penalty | 0 | — |
| DocumentVersion | 0 | — |
| Table | 0 | — |
| TableRow | 0 | — |
| ImageEvidence | 0 | — |

**Edge type breakdown:**

| Edge Type | Count | Family |
|---|---|---|
| CONTAINS | 2,650 | Structural |
| DERIVED_TO_CHUNK | 2,300 | Structural |
| CITES | **0** | Citation |
| ALIAS_OF | **0** | Cross-ref |
| AMENDS | **0** | Cross-doc |
| OVERRIDES | **0** | Cross-doc |
| INVALIDATES | **0** | Cross-doc |
| CONFLICTS_WITH | **0** | Cross-doc |
| REQUIRES | **0** | Cross-doc |
| MENTIONS | **0** | Semantic |
| DEFINES | **0** | Semantic |
| IMPOSES | **0** | Semantic |
| QUALIFIED_BY | **0** | Semantic |
| EXCEPTED_BY | **0** | Semantic |
| *(18 other schema types)* | **0** | — |

100 % of edges are structural. 0 % are semantic, citation, or cross-document.

### 3.2 MongoDB `chunks_vec` — 1,805 chunks

```
Total chunks              : 1,805
With hierarchy_path       : 166   (9%)
With canonical_refs       : ~134  (7%)
With meaningful chunk_type: 1,805 (100%)
```

---

## 4. Root Cause Analysis

### 4.1 [CRITICAL] D4 — Zero CITES edges

**Where it breaks:** `src/pipeline/structurer.py`

`article.citations` is always an empty list in `CanonicalDocument`. The `graph_builder.py` has the wiring to create CITES edges — it checks `for ref in article.citations` — but because `structurer.py` never populates that field, the loop body never executes.

Vietnamese laws cite each other constantly using patterns like:
- `"Theo Điều 15 của Luật này..."`
- `"Căn cứ Khoản 2 Điều 7..."`
- `"Theo quy định tại Điều 10, 11 và 12..."`

None of these are parsed. The fix is entirely in `structurer.py`: add a regex pass over each article's text content to extract these patterns and populate `article.citations`.

**Impact of fix:** Every document would immediately gain 5–50 CITES edges. D4 score: 0 → 7+. D8 density would also improve.

### 4.2 [CRITICAL] D3 — Zero cross-document edges

**Where it breaks:** No cross-document enricher exists.

Vietnamese law has a rich amendment chain. Every new Luật or Nghị định typically amends or supersedes earlier ones. The `raw_data/` folder already contains 29 such documents spanning 2015–2026 (e.g., `92_2015_QH13`, `25_2018_QH14`, `01_2026_QH16`). These almost certainly reference each other.

The graph is built per-document (in `processor.py` → `graph_builder.py`). There is no post-ingestion pass that looks across document pairs to link them.

Signals available for cross-doc matching:
1. **Law number in header** — e.g. "Luật số 92/2015/QH13" — parseable from document text
2. **Amendment phrases** — "sửa đổi, bổ sung một số điều của Luật...", "bãi bỏ Điều X", "thay thế..."
3. **VNLegalText-main dataset** — already in `raw_data/VNLegalText-main/` — contains annotated citation relationships that can serve as ground truth

**Impact of fix:** Transforms the graph from 29 isolated trees into a connected legal knowledge network. This is the highest-value improvement for legal reasoning quality.

### 4.3 [CRITICAL] D5 — Zero semantic concept nodes

**Where it breaks:** Explicitly deferred in `graph_builder.py`

The code contains this comment:
```python
# Semantic edges (MENTIONS, DEFINES, etc.) are not built here —
# they require explicit evidence from a future AI-assisted semantic pass
```

The 17-type node schema defines `Obligation`, `Condition`, `Exception`, `Penalty`, `DefinedTerm`, `Entity`, `LegalConcept`, `Citation` — but none are ever created. The graph cannot answer questions like "which articles impose obligations?" or "what are the exceptions to Article 15?" because that information was never extracted.

Extraction patterns available in Vietnamese law text:
- `Obligation`: "phải...", "có nghĩa vụ...", "bắt buộc..."
- `Condition`: "nếu... thì...", "trong trường hợp... thì..."
- `Exception`: "trừ trường hợp...", "ngoại trừ..."
- `Penalty`: "bị phạt tiền từ...", "phạt cảnh cáo", "tước quyền..."
- `DefinedTerm`: "[X] là...", "được hiểu là..."

### 4.4 [HIGH] D7 — canonical_refs not reaching MongoDB

**Where it breaks:** `src/pipeline/embedding_stage.py` → `embed_chunks_into_mongo()`

The `CanonicalChunk` dataclass has a `canonical_refs` field (list of normalized law references). These refs are used by Stage 3 of the intelligence pipeline — retrieval fusion signal 3 (weight 0.25). Currently only 7% of chunks have this field populated in MongoDB, meaning 93% of the graph-expanded keyword search is providing no signal.

The refs are likely populated correctly in the chunk object in memory but are not being written to the MongoDB document, or they are written under a different field name than what retrieval fusion reads.

### 4.5 [HIGH] D6 — hierarchy_path at 9%

**Where it breaks:** `src/pipeline/chunker.py`, fallback paragraph-group mode

When the chunker cannot identify clear article/section structure (the majority of docs), it falls back to grouping paragraphs. In this fallback mode, `chunk.hierarchy_path` is never set. Only the 9% of chunks that came from structured article extraction carry a path like `["Document:1", "Section:2", "Article:5"]`.

`hierarchy_path` is used for:
1. BM25 retrieval weighting (more specific chunks rank higher)
2. Graph traversal context (which legal position does this chunk belong to?)
3. Admin/debug visibility of where a chunk came from

---

## 5. What the Current Graph Can and Cannot Do

### Can do (D9 = Excellent)
- Navigate the structural hierarchy of any single document
- Find all chunks that belong to a given Article or Section
- Count articles per section, sections per document
- Identify that Chunk C was derived from Article A (DERIVED_TO_CHUNK)

### Cannot do (everything else)
- Answer "Does Law X amend Law Y?" — no AMENDS edges
- Answer "Which laws cite Article 15 of Law 92/2015?" — no CITES edges
- Answer "Which articles impose obligations?" — no Obligation nodes
- Answer "What are the exceptions to this rule?" — no Exception nodes
- Navigate from a chunk to its canonical law reference (7% coverage)
- Know which legal hierarchy level a chunk came from (9% coverage)
- Find "the same article" across two versions of the same law (no ALIAS_OF)

---

## 6. Upgrade Roadmap

### Phase A — Fix data plumbing (1–2 days, highest ROI)

These fixes require no new ML models — pure deterministic parsing.

**A1: Populate `article.citations` in `structurer.py`**

Add a `_extract_citations(text: str) -> list[str]` function that uses regex to find Vietnamese citation patterns in article text:
```python
# Patterns to match:
# "Điều 15", "Khoản 2 Điều 7", "Điều 10, 11 và 12"
# "theo quy định tại Điều ...", "căn cứ Điều ..."
CITATION_RE = re.compile(
    r'(?:theo|căn cứ|quy định tại|xem)?\s*'
    r'(?:khoản\s+\d+\s+)?[Đđ]iều\s+(\d+(?:[,\s]+\d+)*)',
    re.IGNORECASE
)
```
Call this for each article, populate `article.citations`, and `graph_builder.py` will automatically create CITES edges.

Expected result: D4 → 7/10, D8 density → ~1.3

**A2: Set `hierarchy_path` in chunker fallback mode**

In the paragraph-group fallback section of `chunker.py`, assign the nearest ancestor article or section to each chunk's `hierarchy_path`. Even `["Document:doc_id"]` is better than nothing.

Expected result: D6 → 5/15 (Fair)

**A3: Fix `canonical_refs` flow into MongoDB**

Verify that `embed_chunks_into_mongo()` writes `chunk.canonical_refs` to the MongoDB document. Add to the upsert document:
```python
"canonical_refs": chunk.canonical_refs or [],
```
Expected result: D7 → 4/10 (Fair)

**Phase A target score: ~32/100** (still F, but data plumbing is clean)

---

### Phase B — Cross-document legal network (3–5 days)

**B1: Parse law identifiers from document headers**

Each document starts with a header like `"Luật số 92/2015/QH13 ngày 25/11/2015..."`. Extract: law_number (`92/2015`), law_type (`QH`), year, document node ID.

**B2: Build amendment detection**

Scan article text for amendment phrases:
- `"sửa đổi ... Luật số X"` → AMENDS edge
- `"bãi bỏ Điều Y của Luật số X"` → INVALIDATES edge  
- `"thay thế ... bằng ..."` → OVERRIDES edge

Match against the law_number registry built in B1 to identify the target document node.

**B3: Run enricher after all docs are loaded**

Add a `scripts/build_cross_doc_edges.py` enricher that:
1. Loads all graphs from SQLite
2. Builds the law_number → doc_id index
3. Scans all article nodes for amendment phrases
4. Writes new AMENDS/OVERRIDES/INVALIDATES edges back to the graph JSON

Also consult `raw_data/VNLegalText-main/` — it contains annotated citation pairs that can validate and augment this pass.

**Phase B target score: ~50/100** (Grade D — first passing threshold of legal usefulness)

---

### Phase C — Semantic knowledge extraction (5–10 days)

**C1: Obligation / Condition / Exception / Penalty nodes**

Add a `SemanticExtractor` pass in `graph_builder.py` that scans article text with regex (fast, no LLM needed for most patterns):

```python
OBLIGATION_RE   = re.compile(r'(?:phải|có nghĩa vụ|bắt buộc)\s+(.{10,120})', re.DOTALL)
CONDITION_RE    = re.compile(r'(?:nếu|trong trường hợp)\s+(.{5,100})\s+thì\s+(.{10,120})', re.DOTALL)
EXCEPTION_RE    = re.compile(r'trừ trường hợp\s+(.{10,120})', re.DOTALL)
PENALTY_RE      = re.compile(r'(?:phạt tiền từ|phạt cảnh cáo|tước quyền)\s+(.{10,100})', re.DOTALL)
DEFINED_TERM_RE = re.compile(r'"([^"]{3,60})"\s+(?:là|được hiểu là|có nghĩa là)\s+(.{10,200})', re.DOTALL)
```

For each match: create a typed node (Obligation/Condition/Exception/Penalty/DefinedTerm), add an IMPOSES/QUALIFIED_BY/EXCEPTED_BY/DEFINES edge from the parent article.

**Phase C target score: ~72/100** (Grade B)

---

## 7. Expected Score Progression

| Phase | Key changes | Estimated score |
|---|---|---|
| Current | Containment tree only | **18 / 100** |
| After Phase A | Citations parsed, hierarchy_path fixed, canonical_refs in Mongo | **~32 / 100** |
| After Phase B | Cross-doc AMENDS/OVERRIDES network built | **~50 / 100** |
| After Phase C | Semantic nodes: Obligation, Condition, Exception, Penalty, DefinedTerm | **~72 / 100** |
| Full production | ALIAS_OF multilingual, Entity linking, LLM-assisted refinement | **~88 / 100** |

---

## 8. Impact on Retrieval Quality

The intelligence pipeline (Stage 3 — RetrievalFusionEngine) has 4 signals with these weights:

| Signal | Weight | Current quality | After Phase B |
|---|---|---|---|
| Vector search (384-dim cosine) | 0.45 | Working — no change needed | No change |
| BM25 keyword TF | 0.20 | Working | No change |
| **Graph-expanded keyword** | **0.25** | **Near-zero** (7% canonical_refs) | **Full signal** |
| Behavior boost | 0.10 | Working | No change |

Signal 3 (weight 0.25) is currently providing almost no value. After Phase A fixes `canonical_refs` and Phase B builds the cross-doc network, this signal will activate. Queries like "Điều 15 Luật Đất đai" will correctly pull chunks from related amending laws, not just the exact match.

---

## 9. Files to Modify

| File | Phase | Change |
|---|---|---|
| `src/pipeline/structurer.py` | A1 | Add `_extract_citations(text)`, populate `article.citations` |
| `src/pipeline/chunker.py` | A2 | Set `hierarchy_path` in fallback paragraph-group mode |
| `src/pipeline/embedding_stage.py` | A3 | Write `canonical_refs` field to MongoDB upsert document |
| `src/pipeline/graph_builder.py` | B, C | Add cross-doc enricher hook; add semantic extraction pass |
| `scripts/build_cross_doc_edges.py` | B | New script: post-ingestion cross-doc edge builder |
| `src/schemas/graph.py` | — | No changes needed — schema is already correct |

The schema in `src/schemas/graph.py` is well-designed (17 node types, 24 edge types). The problem is entirely in the pipeline code that was supposed to populate it.
