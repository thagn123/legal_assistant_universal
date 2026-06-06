import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.mongodb.client import get_db

db = get_db()
chunks_col = db["chunks_vec"]

with open("search_ly_hon_results.txt", "w", encoding="utf-8") as f:
    f.write("Searching chunks matching 'Chia quyền sử dụng đất':\n")
    count = chunks_col.count_documents({"content": {"$regex": "Chia quyền sử dụng đất", "$options": "i"}})
    f.write(f"Count: {count}\n\n")

    for doc in chunks_col.find({"content": {"$regex": "Chia quyền sử dụng đất", "$options": "i"}}, {"embedding": 0, "_id": 0}).limit(5):
        f.write(f"Chunk ID: {doc.get('chunk_id')}\n")
        f.write(f"Doc ID: {doc.get('doc_id')}\n")
        f.write(f"Law Reference: {doc.get('law_reference')}\n")
        f.write(f"Law Type: {doc.get('law_type')}\n")
        f.write(f"Content Preview: {doc.get('content')[:250]}\n")
        f.write("-" * 50 + "\n")
