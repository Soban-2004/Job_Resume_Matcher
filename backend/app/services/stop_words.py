from functools import lru_cache

import nltk
from nltk.corpus import stopwords


@lru_cache
def load_stopwords() -> set[str]:
    nltk.download("stopwords", quiet=True)
    return set(stopwords.words("english"))
