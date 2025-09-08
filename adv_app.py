import streamlit as st
from core.document_loader import load_document
from analysis.job_seeker import analyze_and_generate
from analysis.recruiter import recruiter_analysis

# =======================
# Page Config
# =======================
st.set_page_config(page_title="AI Resume & Job Matcher", page_icon="🧭", layout="wide")

# =======================
# Header
# =======================
st.markdown(
    """
    <div style="text-align:center; padding:20px 0;">
        <h1>🧭 AI-Powered Resume & Job Matcher</h1>
        <p style="font-size:18px; color:gray;">Smartly match resumes with job descriptions — for job seekers & recruiters</p>
    </div>
    """,
    unsafe_allow_html=True
)

# =======================
# User Mode Selection
# =======================
st.sidebar.title("⚙️ Settings")
mode = st.sidebar.radio("Select User Type:", ["Job Seeker", "Recruiter"])

st.divider()

# =======================
# Job Seeker Mode
# =======================
if mode == "Job Seeker":
    st.subheader("👩‍💼 For Job Seekers")
    st.info("Upload your resume and job description to see how well you match the role.")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            resume_file = st.file_uploader("📄 Upload Resume", type=["pdf", "docx", "txt"])
        with col2:
            job_desc_file = st.file_uploader("💼 Upload Job Description", type=["pdf", "docx", "txt"])

        job_role = st.text_input("✍️ Enter Job Role", placeholder="e.g., Data Scientist, Full-Stack Developer")

    st.markdown("---")
    if st.button("🚀 Analyze Resume Match", use_container_width=True):
        if resume_file and job_desc_file and job_role:
            resume_text = load_document(resume_file)
            job_desc_text = load_document(job_desc_file)
            if resume_text and job_desc_text:
                analyze_and_generate(resume_text, job_desc_text, job_role)
            else:
                st.error("❌ Could not read one or both files.")
        else:
            st.warning("⚠️ Please upload both a resume and job description, and enter the job role.")

# =======================
# Recruiter Mode
# =======================
elif mode == "Recruiter":
    st.subheader("🏢 For Recruiters")
    st.info("Upload job description and multiple resumes to find the best candidates.")

    with st.container():
        job_desc_file = st.file_uploader("💼 Upload Job Description", type=["pdf", "docx", "txt"])
        job_role = st.text_input("✍️ Enter Job Role", placeholder="e.g., Data Scientist, Full-Stack Developer")
        resumes = st.file_uploader("📑 Upload Multiple Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)

    st.markdown("---")
    if st.button("🚀 Analyze Candidates", use_container_width=True):
        if job_desc_file and resumes and job_role:
            job_desc_text = load_document(job_desc_file)
            if job_desc_text:
                recruiter_analysis(job_desc_text, resumes, job_role)
            else:
                st.error("❌ Could not read job description file.")
        else:
            st.warning("⚠️ Please upload a job description and resumes, and enter the job role.")
