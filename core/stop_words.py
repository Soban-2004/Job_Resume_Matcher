import nltk
from nltk.corpus import stopwords
import streamlit as st

@st.cache_resource
def load_stopwords():
    nltk.download("stopwords")

    return set(stopwords.words("english"))
