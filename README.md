# 🚀 AI-Powered Resume & Job Matcher

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg)
![LangChain](https://img.shields.io/badge/LangChain-Integration-green.svg)
![RAG](https://img.shields.io/badge/RAG-Architecture-orange.svg)

An intelligent, dual-mode application designed to bridge the gap between talent and opportunity. Built using **Streamlit**, **LangChain**, and **LLMs**, this tool serves two distinct user bases: **Job Seekers** looking to optimize their ATS scores, and **Recruiters** looking to screen candidates efficiently.

---

## 📹 Project Demos

### 1. For Job Seekers 🧑‍💻
*Analyze your resume against a specific Job Description (JD) to get an ATS score, skill gap analysis, and a tailored cover letter.*

https://github.com/user-attachments/assets/job_seeker_demo.mp4
### 2. For Recruiters 🕵️‍♂️
*Upload a Job Description and bulk-upload multiple resumes to get a ranked table of candidates based on semantic relevance.*

https://github.com/user-attachments/assets/recruiter_demo.mp4
---

## ✨ Key Features

### 🧑‍💻 Job Seeker Mode
- **ATS Score & Summary:** instant evaluation of how well your resume matches the JD.
- **Skill Gap Analysis:** Identifies missing keywords (hard skills & soft skills) critical for the role.
- **Tailored Cover Letter:** Generates a personalized cover letter connecting your experience to the company's needs.
- **Resume Improvement:** Specific, actionable bullet points to improve your CV's impact.

### 🕵️‍♂️ Recruiter Mode
- **Bulk Resume Processing:** Upload 10+ PDF resumes at once.
- **Semantic Ranking:** Ranks candidates not just by keyword matching, but by semantic similarity to the Job Description.
- **Skill Match Grid:** Visual breakdown of which candidates possess the required tech stack.
- **Export to CSV:** Download the ranked list for offline review.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **LLM Orchestration:** LangChain
- **Model:** OpenAI GPT-3.5 / Groq (Configurable)
- **Vector Embeddings:** FAISS / ChromaDB (for semantic search)
- **PDF Processing:** PyPDF2
- **Visualization:** Pandas & Plotly

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/SobanShankar/AI-Resume-Matcher.git](https://github.com/SobanShankar/AI-Resume-Matcher.git)
   cd AI-Resume-Matcher
