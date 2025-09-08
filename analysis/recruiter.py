from core.document_loader import load_document
from core.skill_extractor import extract_weighted_skills_from_jd
from core.matching import compare_resume_to_jd, calculate_overall_fit_score
from core.embeddings import get_hugging_face_embeddings
import streamlit as st
import pandas as pd
from core.degree_extractor import extract_degrees
from core.exp_extractor import extract_experience


embeddings = get_hugging_face_embeddings()
# =======================
# 6️⃣ Recruiter Analysis with Weighted Scoring
# =======================
def recruiter_analysis(job_desc_text, resumes, job_role):
    results = []
    jd_degree = extract_degrees(job_desc_text)
    jd_exp = extract_experience(job_desc_text)

    jd_skill_weights = extract_weighted_skills_from_jd(job_desc_text, job_role)
    print(f"Total Weights : {sum(jd_skill_weights.values())}")
    total_weight = sum(jd_skill_weights.values())

    if total_weight == 0:
        st.error("Job description contains no extractable skills.")
        return
    with st.spinner("Analyzing resumes..."):
        for resume_file in resumes:
            resume_text = load_document(resume_file)
            if not resume_text:
                continue

            resume_degree = extract_degrees(resume_text)
            resume_exp = extract_experience(resume_text)
            reason = []
            eligible = True
            ranking = {'diploma': 1, 'associate': 2, 'bachelor': 3, 'master': 4, 'phd': 5}
            if jd_degree['highest'] and resume_degree['highest']:
                if ranking[resume_degree['highest']] < ranking[jd_degree['highest']]:
                    eligible = False
                    reason.append("❌ Degree specification not matching.")
            if resume_exp < jd_exp:
                eligible = False
                reason.append("❌ Insufficient experience.")

            if not eligible:
                results.append({
                    "Resume": resume_file.name,
                    "Overall Fit Score": 0,
                    "Skill-Based ATS Score": 0,
                    "Matched Skills": "",
                    "Missing Skills": " | ".join(reason)
                })
                continue
                
            analysis_result = compare_resume_to_jd(resume_text, jd_skill_weights, embeddings)
            overall_fit_score = calculate_overall_fit_score(resume_text, job_desc_text, embeddings)

            weighted_score = analysis_result["weighted_score"]
            normalized_score = (weighted_score / total_weight) * 100

            results.append({
                "Resume": resume_file.name,
                "Overall Fit Score": overall_fit_score,
                "Skill-Based ATS Score": normalized_score,
                "Matched Skills": ", ".join(analysis_result["matched_skills"]),
                "Missing Skills": ", ".join(analysis_result["skill_gaps"])
            })

    if results:
        df = pd.DataFrame(results).sort_values("Skill-Based ATS Score", ascending=False)
        st.subheader("Ranked Candidates")
        st.dataframe(df.style.format({"Skill-Based ATS Score": "{:.2f}%", "Overall Fit Score": "{:.2f}%"}), use_container_width=True)

        st.download_button("📥 Download Results (CSV)", 
                           df.to_csv(index=False), 
                           "ats_results.csv", 
                           "text/csv")
    else:
        st.warning("No resumes processed.")