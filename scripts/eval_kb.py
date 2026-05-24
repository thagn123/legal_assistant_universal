#!/usr/bin/env python3
"""Quick knowledge-base quality evaluation."""
from __future__ import annotations
import os, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient

uri = os.environ.get("MONGO_URI", "")
db_name = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
client = MongoClient(uri)
db = client[db_name]

SEP = "=" * 60

chunks = list(db.chunks_vec.find({}, {
    "content": 1, "hierarchy_path": 1, "structure_path": 1,
    "embedding": 1, "user_id": 1, "is_global": 1,
    "source_file": 1, "filename": 1, "doc_id": 1,
    "has_embedding": 1,
}))

total = len(chunks)
if total == 0:
    print("No chunks found -- knowledge base is empty.")
    sys.exit(0)

lens = [len(c.get("content", "")) for c in chunks]
with_emb = sum(1 for c in chunks if c.get("has_embedding") or c.get("embedding"))
with_path = sum(1 for c in chunks if c.get("hierarchy_path", "").strip())
too_short = sum(1 for l in lens if l < 100)
too_long  = sum(1 for l in lens if l > 4000)
good_len  = total - too_short - too_long

avg_len    = sum(lens) // total
median_len = sorted(lens)[total // 2]

print(SEP)
print("KNOWLEDGE BASE EVALUATION REPORT")
print(SEP)

print("\n[1] CHUNK STATISTICS")
print(f"  Total chunks        : {total}")
print(f"  Global (is_global)  : {sum(1 for c in chunks if c.get('is_global'))}")
print(f"  Length avg / median : {avg_len} / {median_len} chars")
print(f"  Length min / max    : {min(lens)} / {max(lens)} chars")
print(f"  Good length [100-4000]: {good_len} ({100*good_len/total:.0f}%)")
print(f"  Too short (<100)    : {too_short}")
print(f"  Too long  (>4000)   : {too_long}")

emb_pct = 100 * with_emb / total
print("\n[2] EMBEDDING COVERAGE")
print(f"  With embedding    : {with_emb} / {total}  ({emb_pct:.1f}%)")
print(f"  Without embedding : {total - with_emb}")
sample_emb = next((c["embedding"] for c in chunks if c.get("embedding")), None)
if sample_emb:
    print(f"  Dimensions        : {len(sample_emb)}")

path_pct = 100 * with_path / total
print("\n[3] STRUCTURE / HIERARCHY")
print(f"  With hierarchy_path    : {with_path} ({path_pct:.0f}%)")
print(f"  Without hierarchy_path : {total - with_path}")

sources = Counter(
    c.get("source_file") or c.get("filename") or (c.get("doc_id", "unknown")[:12])
    for c in chunks
)
print(f"\n[4] SOURCE DOCUMENTS ({len(sources)} unique)")
for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
    bar = "#" * min(cnt, 40)
    print(f"  {cnt:3d}  {bar}  {src}")

templates = list(db.templates.find({}, {"name": 1, "template_type": 1, "embedding": 1, "industry": 1}))
t_types   = Counter(t.get("template_type", "contract") for t in templates)
t_emb     = sum(1 for t in templates if t.get("embedding"))
print(f"\n[5] TEMPLATES & OFFICIAL FORMS ({len(templates)} total)")
for tt, cnt in t_types.items():
    print(f"  {tt}: {cnt}")
print(f"  With embedding: {t_emb} / {len(templates)}")

# ── Scoring ──────────────────────────────────────────────────────────────────
score   = 0
details = []

if emb_pct >= 95:   s = 30; lbl = "Excellent"
elif emb_pct >= 80: s = 22; lbl = "Good"
elif emb_pct >= 60: s = 14; lbl = "Fair"
else:                s =  5; lbl = "Poor"
score += s; details.append(f"  Embedding coverage {emb_pct:.0f}%           -> {s}/30  [{lbl}]")

good_pct = 100 * good_len / total
if good_pct >= 80:   s = 25; lbl = "Excellent"
elif good_pct >= 60: s = 18; lbl = "Good"
elif good_pct >= 40: s = 10; lbl = "Fair"
else:                 s =  3; lbl = "Poor"
score += s; details.append(f"  Chunk length quality {good_pct:.0f}%         -> {s}/25  [{lbl}]")

if len(sources) >= 20:   s = 20; lbl = "Excellent"
elif len(sources) >= 10: s = 15; lbl = "Good"
elif len(sources) >= 5:  s =  9; lbl = "Fair"
else:                     s =  3; lbl = "Poor"
score += s; details.append(f"  Source diversity {len(sources)} unique files  -> {s}/20  [{lbl}]")

if path_pct >= 80:   s = 15; lbl = "Excellent"
elif path_pct >= 50: s = 10; lbl = "Good"
elif path_pct >= 20: s =  5; lbl = "Fair"
else:                 s =  1; lbl = "Poor"
score += s; details.append(f"  Hierarchy path coverage {path_pct:.0f}%      -> {s}/15  [{lbl}]")

if len(templates) >= 40:   s = 10; lbl = "Excellent"
elif len(templates) >= 20: s =  7; lbl = "Good"
elif len(templates) >= 10: s =  4; lbl = "Fair"
else:                       s =  1; lbl = "Poor"
score += s; details.append(f"  Templates + official forms {len(templates)}   -> {s}/10  [{lbl}]")

grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"

print(f"\n{SEP}")
print(f"OVERALL SCORE:  {score}/100  (Grade: {grade})")
print(SEP)
for d in details:
    print(d)

print("\nCONCLUSION:")
if score >= 90:
    print("  Knowledge base is production-ready. Vector search will be highly accurate.")
elif score >= 75:
    print("  Knowledge base is good. Minor gaps worth addressing.")
elif score >= 60:
    print("  Knowledge base is usable but has quality issues worth fixing.")
elif score >= 45:
    print("  Knowledge base needs improvement before production use.")
else:
    print("  Knowledge base is critically incomplete.")
print()
