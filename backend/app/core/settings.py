"""Centralized environment-driven settings.

All hardcoded values (URLs, model names, limits) are externalized here.
Defaults match local development — override via environment variables.
"""
import os

# --- Ollama ---
OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3.1")

# --- Embedding ---
EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-m3")

# --- PDF Ingestion ---
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "2048"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "200"))
EMBEDDING_BATCH_SIZE: int = int(os.environ.get("EMBEDDING_BATCH_SIZE", "10"))
