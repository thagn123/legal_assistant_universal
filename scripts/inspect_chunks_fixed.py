import os
import sys
from src.mongodb.client import get_db

db = get_db()
chunks_col = db["chunks_vec"]

with open("inspect_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Total chunks in MongoDB: {chunks_col.count_documents({})}\n\n")

    # Group by law_type
    pipeline = [
        {"$group": {"_id": "$law_type", "count": {"$sum": 1}}}
    ]
    f.write("Chunks by law_type:\n")
    for r in chunks_col.aggregate(pipeline):
        f.write(f"  {r['_id']}: {r['count']}\n")

    # Sample some chunks that mention "Điều 62"
    f.write("\nSample chunks matching 'Điều 62':\n")
    for c in chunks_col.find({"content": {"$regex": "Điều 62", "$options": "i"}}, {"_id": 0, "embedding": 0}).limit(10):
        f.write(f"  chunk_id: {c.get('chunk_id')}\n")
        f.write(f"  law_type: {c.get('law_type')}\n")
        f.write(f"  law_ref:  {c.get('law_reference')}\n")
        f.write(f"  content:  {c.get('content')[:200]}...\n\n")

    # Let's search for "đất" or "thu hồi" under dat_dai law_type
    f.write("\nSample chunks under 'dat_dai':\n")
    for c in chunks_col.find({"law_type": "dat_dai"}, {"_id": 0, "embedding": 0}).limit(10):
        f.write(f"  chunk_id: {c.get('chunk_id')}\n")
        f.write(f"  law_ref:  {c.get('law_reference')}\n")
        f.write(f"  content:  {c.get('content')[:200]}...\n\n")
