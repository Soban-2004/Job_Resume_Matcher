import streamlit as st
from core.degree_extractor import extract_degrees
from core.skill_extractor import extract_weighted_skills_from_jd
from core.matching import compare_resume_to_jd
from core.embeddings import get_hugging_face_embeddings
from core.matching import calculate_overall_fit_score
from core.llm import load_llm
from core.exp_extractor import extract_experience

embeddings = get_hugging_face_embeddings()
llm = load_llm()
# =======================
# 5️⃣ Job Seeker Analysis
# =======================
def analyze_and_generate(resume_text, job_desc_text, job_role):
    st.subheader("Analysis Results")

        # 🎓 Extract degree info
    resume_degree = extract_degrees(resume_text)
    jd_degree = extract_degrees(job_desc_text)

    resume_exp = extract_experience(resume_text)
    jd_exp = extract_experience(job_desc_text)

    st.write(f"**Resume Highest Degree:** {resume_degree['highest']}")
    st.write(f"**Job Requirement Degree:** {jd_degree['highest']}")


    # Eligibility check
    ranking = {'diploma': 1, 'associate': 2, 'bachelor': 3, 'master': 4, 'phd': 5}
    if jd_degree['highest'] and resume_degree['highest']:
        if ranking[resume_degree['highest']] < ranking[jd_degree['highest']]:
            st.error("❌ Degree specification not matching. You are not eligible to apply.")
            return
    else:
        st.warning("⚠️ Could not determine degrees from text. Proceeding with skill analysis...")
    
    st.write(f"**Resume Experience:** {resume_exp} years")
    st.write(f"**Job Requirement Experience:** {jd_exp} years")
    if resume_exp < jd_exp:
        st.error("❌ Experience requirement not satisfied. You are not eligible to apply.")
        return
    with st.spinner("Analyzing..."):
        jd_skill_weights = extract_weighted_skills_from_jd(job_desc_text, job_role)
        print(f"Total JD Skill Weight: {sum(jd_skill_weights.values())}")
        analysis_result = compare_resume_to_jd(resume_text, jd_skill_weights, embeddings)
        overall_fit_score = calculate_overall_fit_score(resume_text, job_desc_text, embeddings)

    resume_skills = analysis_result["resume_skills"]
    print(f"Resume Skills : {len(resume_skills)}")
    jd_skills = analysis_result["jd_skills"]
    print(f"\nJob Description skills : {len(jd_skills)}")
    matched_skills = analysis_result["matched_skills"]
    skill_gaps = analysis_result["skill_gaps"]
    skill_mapping = analysis_result["skill_mapping"]
    
    # Calculate the normalized ATS score for display
    total_possible_score = sum(jd_skill_weights.values())
    weighted_score = analysis_result["weighted_score"]
    print(f"\nWeighted Score for this resume: {weighted_score}")
    normalized_score = (weighted_score / total_possible_score) * 100 if total_possible_score > 0 else 0
    print(f"\nthe Ats is : {normalized_score}")
    # ATS scoring with semantic reasoning
    ats_score_prompt = """
    You are an expert resume analyst. 
    Carefully evaluate the following analysis. Consider semantic similarity between skills
    (e.g., 'eda' ≈ 'data analysis', 'power bi' ≈ 'kpi dashboards'). 
    Do not count conceptually covered skills as missing.

    Provide:
    1. ATS Score (1-100)
    2. Summary of strengths
    3. Gap-filling suggestions (3-5 points)

    Resume Skills: {resume_skills}
    Job Description Skills: {jd_skills}
    Matched Skills: {matched_skills}
    Missing Skills: {missing_skills}
    """
    ats_response = llm.invoke(ats_score_prompt.format(
        resume_skills=", ".join(resume_skills),
        jd_skills=", ".join(jd_skills),
        matched_skills=", ".join(matched_skills),
        missing_skills=", ".join(skill_gaps)
    ))

    # Cover letter
    cover_letter_prompt = """
    Write a professional, 3-paragraph cover letter based on the resume and job description. 
    Highlight relevant skills, experiences, and motivation.

    Resume: {resume_text}
    Job Description: {job_desc_text}
    """
    cover_letter_response = llm.invoke(cover_letter_prompt.format(
        resume_text=resume_text,
        job_desc_text=job_desc_text
    ))

    # Resume improvement tips
    improvement_prompt = """
    You are a career advisor. Suggest improvements for the resume to better align with the job description.
    Provide 3–7 actionable bullet points.

    Resume: {resume_text}
    Job Description: {job_desc_text}
    """
    improvement_response = llm.invoke(improvement_prompt.format(
        resume_text=resume_text,
        job_desc_text=job_desc_text
    ))

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["ATS Score & Summary", "Matched Skills", "Skill Gaps", "Cover Letter", "Resume Improvement"]
    )

    with tab1:
        st.markdown(f"### Overall Semantic Fit Score: {overall_fit_score:.2f}%")
        st.markdown(f"### Skill-Based ATS Score: {normalized_score:.2f}%")
        st.write("Overall ATS Score and Review by AI")
        st.write(ats_response.content)

    with tab2:
        st.markdown("### Matched Skills")
        if matched_skills:
            for r_skill, jd_matches in skill_mapping.items():
                if any(dist <= 0.45 for jd_skill, dist in jd_matches):
                    st.markdown(f"**Your Skill:** `{r_skill}`")
                    for jd_skill, dist in jd_matches:
                        if dist <= 0.45:
                            st.write(f"- `{jd_skill}` (Similarity: {1 - dist:.2f})")
                    st.markdown("---")
        else:
            st.write("No significant skill matches found.")

    with tab3:
        st.markdown("### Identified Skill Gaps")
        if skill_gaps:
            for skill in skill_gaps:
                st.markdown(f"• **`{skill}`**")
        else:
            st.write("No significant gaps found.")

    with tab4:
        st.markdown("### Tailored Cover Letter")
        st.write(cover_letter_response.content)

    with tab5:
        st.markdown("### Resume Improvement Suggestions")
        st.write(improvement_response.content)
