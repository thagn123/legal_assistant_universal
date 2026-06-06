import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
import os

uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/?directConnection=true")
client = MongoClient(uri)

print("Databases list:", client.list_database_names())

for db_name in client.list_database_names():
    if db_name in ("admin", "config", "local"):
        continue
    db = client[db_name]
    print(f"\nSearching database: {db_name}")
    for name in db.list_collection_names():
        col = db[name]
        try:
            count = col.count_documents({"$or": [
                {"content": {"$regex": "52_2014_QH13_238640", "$options": "i"}},
                {"filename": {"$regex": "52_2014_QH13_238640", "$options": "i"}},
                {"doc_id": {"$regex": "83a4e26e", "$options": "i"}},
                {"title": {"$regex": "Ly hôn", "$options": "i"}},
                {"law_reference": {"$regex": "52_2014", "$options": "i"}}
            ]})
            print(f"  Collection '{name}' matches: {count}")
            if count > 0:
                for doc in col.find({"$or": [
                    {"content": {"$regex": "52_2014_QH13_238640", "$options": "i"}},
                    {"filename": {"$regex": "52_2014_QH13_238640", "$options": "i"}},
                    {"doc_id": {"$regex": "83a4e26e", "$options": "i"}},
                    {"title": {"$regex": "Ly hôn", "$options": "i"}},
                    {"law_reference": {"$regex": "52_2014", "$options": "i"}}
                ]}, {"embedding": 0, "_id": 0}).limit(2):
                    print("    Sample:", str(doc)[:250])
        except Exception as e:
            print(f"  Error reading '{name}': {e}")
