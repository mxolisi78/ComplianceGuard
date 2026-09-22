"""
Vector store for compliance rules.
Reuses the DocuChat pattern: sentence-transformers + ChromaDB.
"""
from pathlib import Path
from typing import List, Dict
import chromadb
from sentence_transformers import SentenceTransformer

from src.config import CHROMA_DIR, EMBED_MODEL, COLLECTION_NAME

_embedder = None
_client = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def add_rules(rules: List[Dict]) -> int:
    """
    rules = [{"id": "GDPR-5", "text": "...", "category": "data_privacy"}, ...]
    """
    if not rules:
        return 0

    embedder = get_embedder()
    collection = get_collection()

    ids = [r["id"] for r in rules]
    texts = [r["text"] for r in rules]
    metadatas = [{"id": r["id"], "category": r.get("category", "general")} for r in rules]
    embeddings = embedder.encode(texts, normalize_embeddings=True).tolist()

    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    return len(rules)


def search_rules(query: str, top_k: int = 4) -> List[Dict]:
    embedder = get_embedder()
    collection = get_collection()

    if collection.count() == 0:
        return []

    vec = embedder.encode([query], normalize_embeddings=True).tolist()
    results = collection.query(
        query_embeddings=vec,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "id": meta.get("id", ""),
            "category": meta.get("category", "general"),
            "score": round(1.0 - dist, 4),
        })
    return hits


def count() -> int:
    return get_collection().count()


def reset():
    global _client
    try:
        get_client().delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    _client = None