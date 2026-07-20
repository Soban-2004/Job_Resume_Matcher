from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import settings
from app.core.gpu_lock import run_on_gpu_thread


@lru_cache
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model)


def rerank(query: str, candidates: list[str]) -> list[float]:
    """Returns a relevance score per candidate, same order as input."""
    if not candidates:
        return []

    def _predict() -> list[float]:
        model = get_reranker()
        pairs = [(query, candidate) for candidate in candidates]
        return [float(s) for s in model.predict(pairs)]

    return run_on_gpu_thread(_predict)
