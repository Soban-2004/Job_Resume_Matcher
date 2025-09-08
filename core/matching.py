from sklearn.metrics.pairwise import cosine_distances, cosine_similarity
from core.skill_extractor import extract_skills
import re
from core.stop_words import load_stopwords
from core.embeddings import get_hugging_face_embeddings

embeddings_model = get_hugging_face_embeddings()

stop_words = load_stopwords()
# =======================
# 3️⃣ Skill Matching with Weighted Scoring
# =======================
def compute_skill_distances(resume_skills, jd_skills, embeddings_model):
    resume_vectors = embeddings_model.embed_documents(resume_skills)
    jd_vectors = embeddings_model.embed_documents(jd_skills)
    distances = cosine_distances(resume_vectors, jd_vectors)

    detailed_mapping = {}
    for i, r_skill in enumerate(resume_skills):
        detailed_mapping[r_skill] = {}  
        for j, jd_skill in enumerate(jd_skills):
            detailed_mapping[r_skill][jd_skill] = distances[i][j]
    return detailed_mapping

def compare_resume_to_jd(resume_text, jd_skill_weights, embeddings_model, threshold=0.45):
    """Compares resume skills to weighted JD skills."""
    resume_skills = extract_skills(resume_text)
    print(f"Resume skill list : {resume_skills}")
    jd_skills = list(jd_skill_weights.keys())
    
    
    if not resume_skills or not jd_skills:
        return {
            "resume_skills": [],
            "jd_skills": jd_skills,
            "weighted_score": 0,
            "matched_skills": [],
            "skill_gaps": jd_skills,
            "skill_mapping": {},
            "distance_matrix": {}
        }

    distance_matrix = compute_skill_distances(resume_skills, jd_skills, embeddings_model)
    weighted_score = 0
    matched_skills_set = set()
    skill_mapping = {}

    for r_skill in resume_skills:
        skill_mapping[r_skill] = []
        for jd_skill, dist in distance_matrix[r_skill].items():
             if dist <= threshold and jd_skill not in matched_skills_set:
                # semantic_weight = 1 - dist
                # weight = jd_skill_weights.get(jd_skill, 0.5)
                # final_skill_score = semantic_weight * weight
                # weighted_score += final_skill_score
                # matched_skills_set.add(jd_skill)
                weight = jd_skill_weights.get(jd_skill, 1)  # use JD-defined importance
                weighted_score += weight  # no semantic factor
                matched_skills_set.add(jd_skill)
                skill_mapping[r_skill].append((jd_skill, dist))

        if not skill_mapping[r_skill]:
            if distance_matrix[r_skill]:
                closest_jd = min(distance_matrix[r_skill], key=distance_matrix[r_skill].get)
                closest_distance = distance_matrix[r_skill][closest_jd]
                skill_mapping[r_skill].append((closest_jd, closest_distance))
    
    skill_gaps = [skill for skill in jd_skills if skill not in matched_skills_set]
    

    return {
        "resume_skills": resume_skills,
        "jd_skills": jd_skills,
        "weighted_score": weighted_score,
        "matched_skills": list(matched_skills_set),
        "skill_gaps": skill_gaps,
        "skill_mapping": skill_mapping,
        "distance_matrix": distance_matrix
    }

def preprocess_text(text: str) -> str:
    """
    Preprocess text by:
    - Lowercasing
    - Removing non-alphanumeric characters (except spaces)
    - Removing stopwords
    - Stripping extra spaces
    """
    # Lowercase
    text = text.lower()
    
    # Remove special characters (keep words and numbers)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    
    # Remove stopwords
    words = [word for word in text.split() if word not in stop_words]
    
    # Rebuild text
    return " ".join(words).strip()

def calculate_overall_fit_score(resume_text, jd_text, embeddings_model):
    """
    Calculates the cosine similarity between the full resume and job description texts.
    Returns a score from 0-100%.
    """
    if not resume_text or not jd_text:
        return 0
    # Preprocess
    resume_text_clean = preprocess_text(resume_text)
    jd_text_clean = preprocess_text(jd_text)
    
    # Embed
    resume_vector = embeddings_model.embed_documents([resume_text_clean])[0]
    jd_vector = embeddings_model.embed_documents([jd_text_clean])[0]
    # resume_vector = embeddings_model.embed_documents([resume_text])[0]
    # jd_vector = embeddings_model.embed_documents([jd_text])[0]
    
    similarity = cosine_similarity([resume_vector], [jd_vector])[0][0]
    return (similarity * 100) + 5
