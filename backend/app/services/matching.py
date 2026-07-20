import re

from sklearn.metrics.pairwise import cosine_similarity

from app.core.embeddings import embed_texts
from app.services.stop_words import load_stopwords


def preprocess_text(text: str) -> str:
    """Lowercase, strip non-alphanumerics, drop stopwords."""
    stop_words = load_stopwords()
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [word for word in text.split() if word not in stop_words]
    return " ".join(words).strip()


def calculate_overall_fit_score(resume_text: str, jd_text: str) -> float:
    """Cosine similarity between full resume and JD text, as a 0-100 score.

    This is a holistic gestalt-similarity signal, distinct from the
    evidence-grounded per-requirement scoring in rag_matching.py.
    """
    if not resume_text or not jd_text:
        return 0.0

    resume_text_clean = preprocess_text(resume_text)
    jd_text_clean = preprocess_text(jd_text)

    vectors = embed_texts([resume_text_clean, jd_text_clean])
    similarity = cosine_similarity([vectors[0]], [vectors[1]])[0][0]
    return min(100.0, max(0.0, float(similarity) * 100 + 5))
