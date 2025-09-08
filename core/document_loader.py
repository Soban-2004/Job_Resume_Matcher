import docx2txt
import PyPDF2
import streamlit as st
# =======================
# 4️⃣ Document Loader
# =======================
def load_document(uploaded_file):
    try:
        if uploaded_file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        elif uploaded_file.name.endswith('.docx'):
            with open("temp.docx", "wb") as f:
                f.write(uploaded_file.read())
            return docx2txt.process("temp.docx")
        elif uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8", errors="ignore")
        else:
            return None
    except Exception as e:
        st.error(f"Error loading document: {e}")
        return None