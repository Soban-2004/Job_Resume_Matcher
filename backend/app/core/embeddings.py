from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.core.gpu_lock import run_on_gpu_thread


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    # gte-base-en-v1.5 still supports 8192 tokens despite its small size
    # (unlike all-MiniLM-L6-v2's 256-token cap, which silently truncated
    # full resume/JD text). It uses custom modeling code from its HF repo,
    # hence trust_remote_code -- a well-known, widely used model.
    return SentenceTransformer(settings.embedding_model, trust_remote_code=True)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Returns L2-normalized embeddings, so a dot product equals cosine similarity."""
    if not texts:
        return np.empty((0, 0))

    def _encode() -> np.ndarray:
        model = get_embedding_model()
        return np.asarray(model.encode(texts, normalize_embeddings=True, show_progress_bar=False))

    return run_on_gpu_thread(_encode)
