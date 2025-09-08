from langchain_huggingface import HuggingFaceEmbeddings

@st.cache_resource
def get_hugging_face_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
