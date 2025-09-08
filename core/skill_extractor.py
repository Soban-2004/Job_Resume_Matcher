from langchain_core.prompts import ChatPromptTemplate
import re
import json
import streamlit as st  
from core.llm import load_llm

def extract_skills(text: str):
    """Extracts a flat list of skills from a text."""
    # Prompt for general skill extraction (used for resume)
    prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert resume parsing assistant. "
     "Your ONLY task is to extract technical skills, programming languages, tools, "
     "frameworks, libraries, platforms, cloud services, databases, and methodologies "
     "from the given resume text.\n"
     "Strict rules:\n"
     "1. Extract skills explicitly mentioned in the text, from ANY section (technical skills, projects, internships, certifications, etc.).\n"
     "2. EXCLUDE soft skills (e.g., communication, leadership, teamwork, creativity, adaptability, problem-solving, collaboration, attention to detail).\n"
     "3. Keep multi-word skills exactly as written (e.g., 'natural language processing', 'power bi').\n"
     "4. Everything must be lowercase.\n"
     "5. Remove duplicates.\n"
     "6. Do not hallucinate, infer, or generalize. Only include what is explicitly written.\n"
     "7. Return output ONLY as valid JSON in the format: {{\"skills\": [\"...\"]}}.\n"
     "8. Output must contain no commentary or explanation."),
    
    ("user",
     "Extract ALL technical skills, tools, technologies, frameworks, libraries, platforms, "
     "cloud services, databases, and methodologies mentioned in the following text. "
     "Return the results strictly as JSON.\n\nText:\n{text}")
])




    chain = prompt_template | load_llm()
    response = chain.invoke({"text": text})
    try:
        # Use regex to find the JSON object and parse it
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            skills_dict = json.loads(json_match.group())
            return skills_dict.get('skills', [])
        else:
            print("Warning: No JSON object found in LLM response.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response: {e}")
        print(f"Raw response was: {response.content}")
        return []
    

def extract_weighted_skills_from_jd(jd_text: str, job_role: str):
    """Extracts a dictionary of skills and importance scores from a text."""
    prompt_template = ChatPromptTemplate.from_messages([
        ("system",
        "You are an expert career advisor. Your task is to extract ONLY technical skills, "
        "tools, technologies, platforms, cloud services, databases, frameworks, and methodologies "
        "from a Job Description (JD). STRICTLY exclude soft skills such as communication, leadership, "
        "creativity, problem-solving, teamwork, adaptability, interpersonal skills, and similar. "
        "Do NOT hallucinate skills. Return only skills explicitly mentioned in the JD."),
        
        ("user",
        "Extract all technical skills from the following Job Description and assign importance weights "
        "based on the job role '{role}'. Output as a JSON dictionary where keys are skills (lowercase) "
        "and values are weights between 0 (least important) and 1 (most important). "
        "Keep multi-word skills together.\n\nJD:\n{text}")
    ])

    chain = prompt_template | load_llm()
    try:
        response = chain.invoke({"text": jd_text, "role": job_role})
        text = response.content.strip()

        # Extract JSON using regex
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM response")
        
        weighted_skills_dict = json.loads(match.group())
        print(f"Weighted jd skill list : {weighted_skills_dict}")
        return {k.lower(): float(v) for k, v in weighted_skills_dict.items()}

    except Exception as e:
        st.error(f"Error parsing LLM output: {e}")
        st.write("Raw response:", response.content)
        return {}
