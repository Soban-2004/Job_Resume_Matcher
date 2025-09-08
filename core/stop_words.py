import nltk
from nltk.corpus import stopwords

@st.cache_resource
def load_stopwords():
    nltk.download("stopwords")
    return set(stopwords.words("english"))