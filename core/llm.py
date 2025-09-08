from langchain_groq import ChatGroq
import streamlit as st

@st.cache_resource
def load_llm():
    return ChatGroq(
    groq_api_key=st.secrets["GROQ_API_KEY"],
    model_name="llama-3.1-8b-instant"
)