"""
One-shot script: embed all chunks_vec documents that have no 'embedding' field.
Run inside the API Docker container:
  docker exec -it universallegalknowledgeassistant-api-1 python scripts/embed_seed_chunks.py
"""
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("embed_seed")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/?directConnection=true")
MONGO_DB  = os.environ.get("MONGO_DB", "legal_knowledge_assistant")
BATCH_SIZE = 32
COLLECTION = "chunks_vec"

def main():
    import pymongo
    from sentence_transformers import SentenceTransformer

    log.info("Connecting to %s / %s", MONGO_URI, MONGO_DB)
    client = pymongo.MongoClient(MONGO_URI)
    col = client[MONGO_DB][COLLECTION]

    total = col.count_documents({"embedding": {"$exists": False}})
    log.info("Chunks without embedding: %d", total)
    if total == 0:
        log.info("Nothing to do.")
        return

    log.info("Loading paraphrase-multilingual-MiniLM-L12-v2 (CPU) …")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    log.info("Model loaded.")

    done = 0
    cursor = col.find({"embedding": {"$exists": False}}, {"_id": 1, "content": 1})
    batch_ids, batch_texts = [], []

    def flush(ids, texts):
        vecs = model.encode(texts, normalize_embeddings=True, batch_size=BATCH_SIZE,
                            show_progress_bar=False)
        ops = [
            pymongo.UpdateOne({"_id": ids[i]}, {"$set": {"embedding": vecs[i].tolist()}})
            for i in range(len(ids))
        ]
        col.bulk_write(ops, ordered=False)
        return len(ids)

    for doc in cursor:
        batch_ids.append(doc["_id"])
        batch_texts.append(doc.get("content") or "")
        if len(batch_ids) >= BATCH_SIZE:
            done += flush(batch_ids, batch_texts)
            batch_ids, batch_texts = [], []
            if done % 320 == 0:
                log.info("Progress: %d / %d (%.1f%%)", done, total, done / total * 100)

    if batch_ids:
        done += flush(batch_ids, batch_texts)

    log.info("Done. Embedded %d chunks.", done)
    remaining = col.count_documents({"embedding": {"$exists": False}})
    log.info("Remaining without embedding: %d", remaining)

if __name__ == "__main__":
    main()
