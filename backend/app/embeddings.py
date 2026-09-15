"""Embedding-Modell für Suchanfragen (Lazy-Loading, einmalig)."""

from sentence_transformers import SentenceTransformer
import torch

MODEL_NAME = "intfloat/multilingual-e5-base"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(MODEL_NAME, device=device)
        _model.max_seq_length = 512
    return _model


def embed_query(text: str) -> list[float]:
    """Embedded eine Suchanfrage mit dem e5-Konventions-Prefix 'query: '."""
    model = get_model()
    vec = model.encode(f"query: {text.strip()}", normalize_embeddings=True)
    return vec.tolist()