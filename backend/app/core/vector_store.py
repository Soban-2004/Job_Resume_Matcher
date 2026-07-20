import threading
from functools import lru_cache
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.core.embeddings import embed_texts

COLLECTION_NAME = "resume_chunks"
VECTOR_SIZE = 768  # Alibaba-NLP/gte-base-en-v1.5 dense embedding dimension

# Recruiter batches call upsert_chunks (and therefore ensure_collection) from
# several concurrent candidate threads. Without this, multiple threads can
# all see collection_exists() == False on a fresh collection and race to
# create it, and every loser gets a 409 Conflict from Qdrant.
_ENSURE_COLLECTION_LOCK = threading.Lock()


@lru_cache
def get_qdrant_client() -> QdrantClient:
    # Explicit timeout so a stalled connection fails loudly instead of
    # blocking a worker thread forever.
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30.0)


def ensure_collection() -> None:
    with _ENSURE_COLLECTION_LOCK:
        client = get_qdrant_client()
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
            )

        # Qdrant Cloud requires an explicit payload index before these fields
        # can be used in a filter (scroll/delete) -- create them if missing.
        info = client.get_collection(COLLECTION_NAME)
        existing = set(info.payload_schema.keys()) if info.payload_schema else set()
        for field in ("batch_id", "filename"):
            if field not in existing:
                client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )


def _filter_for(batch_id: str, filename: str) -> qmodels.Filter:
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(key="batch_id", match=qmodels.MatchValue(value=batch_id)),
            qmodels.FieldCondition(key="filename", match=qmodels.MatchValue(value=filename)),
        ]
    )


def upsert_chunks(batch_id: str, filename: str, chunks: list[str]) -> None:
    """Embeds and durably stores a document's chunks, tagged for later retrieval."""
    if not chunks:
        return
    ensure_collection()
    client = get_qdrant_client()
    vectors = embed_texts(chunks)
    points = [
        qmodels.PointStruct(
            id=str(uuid4()),
            vector=vectors[i].tolist(),
            payload={
                "batch_id": batch_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunks[i],
            },
        )
        for i in range(len(chunks))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def fetch_chunks(batch_id: str, filename: str) -> list[dict]:
    """Returns every stored chunk (text + vector) for one document.

    Retrieval-time ranking (BM25 + dense fusion + rerank) runs locally against
    this small, per-document set rather than issuing a Qdrant ANN query --
    Qdrant's job here is durable storage, not runtime search, since a single
    resume is only a few dozen chunks.
    """
    client = get_qdrant_client()
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=_filter_for(batch_id, filename),
        limit=1000,
        with_vectors=True,
        with_payload=True,
    )
    return [
        {"id": p.id, "text": p.payload["text"], "chunk_index": p.payload["chunk_index"], "vector": p.vector}
        for p in points
    ]


def delete_document(batch_id: str, filename: str) -> None:
    """Removes a document's chunks -- used for ephemeral (job-seeker) uploads.

    Deletes by explicit point ID (via fetch_chunks) rather than by filter --
    a filter-based delete depends on the batch_id/filename payload index being
    fully caught up, which can lag just after the index is first created on a
    fresh collection. Point-ID deletion is a direct primary-key operation and
    has no such window.
    """
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return
    chunks = fetch_chunks(batch_id, filename)
    if not chunks:
        return
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=qmodels.PointIdsList(points=[c["id"] for c in chunks]),
    )
