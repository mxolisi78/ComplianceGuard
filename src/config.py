"""
Central configuration for ComplianceGuard.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get(key: str, default=None):
    return os.getenv(key, default)


# === Paths ===
UPLOAD_DIR = PROJECT_ROOT / get("UPLOAD_DIR", "data/uploads")
RULES_DIR = PROJECT_ROOT / get("RULES_DIR", "data/rules")
CHROMA_DIR = PROJECT_ROOT / get("CHROMA_DIR", "data/chroma_db")

for p in (UPLOAD_DIR, RULES_DIR, CHROMA_DIR):
    p.mkdir(parents=True, exist_ok=True)

# === LLM ===
LLM_PROVIDER = get("LLM_PROVIDER", "groq")
GROQ_API_KEY = get("GROQ_API_KEY")
LLM_MODEL = get("LLM_MODEL", "openai/gpt-oss-120b")

# === Embeddings ===
EMBED_MODEL = get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# === Chunking ===
CHUNK_SIZE = int(get("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(get("CHUNK_OVERLAP", 50))

# === Retrieval ===
TOP_K = int(get("TOP_K", 4))

# === Chroma ===
COLLECTION_NAME = get("COLLECTION_NAME", "compliance_rules")