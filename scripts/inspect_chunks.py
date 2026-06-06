import os
import sys
from src.mongodb.client import get_db

db = get_db()
chunks_col = db["chunks_vec"]

print("Total chunks in MongoDB:", chunks_col.count_documents({}))

# Group by law_type
pipeline = [
    {"$group": {"_id": "$law_type", "count": {"$sum": 1}}}
]
print("\nChunks by law_type:")
for r in chunks_col.aggregate(pipeline):
    print(f"  {r['_id']}: {r['count']}")

# Sample some chunks that mention "Ly hôn" or "Điều 62"
print("\nSample chunks matching 'Điều 62':")
for c in chunks_col.find({"content": {"$regex": "Điều 62", "$options": "i"}}, {"_id": 0, "embedding": 0}).limit(5):
    print(f"  chunk_id: {c.get('chunk_id')}")
    print(f"  law_type: {c.get('law_type')}")
    print(f"  law_ref:  {c.get('law_reference')}")
    print(f"  content:  {c.get('content')[:120]}...\n")

# Let's search for "đất" or "thu hồi" under dat_dai law_type
print("\nSample chunks under 'dat_dai':")
for c in chunks_col.find({"law_type": "dat_dai"}, {"_id": 0, "embedding": 0}).limit(5):
    print(f"  chunk_id: {c.get('chunk_id')}")
    print(f"  law_ref:  {c.get('law_reference')}")
    print(f"  content:  {c.get('content')[:120]}...\n")
