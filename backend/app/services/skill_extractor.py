from app.core.llm import call_structured
from app.models.schemas import WeightedSkillList

_WEIGHTED_SKILL_SYSTEM = (
    "You are an expert career advisor. Your task is to extract ONLY technical skills, "
    "tools, technologies, platforms, cloud services, databases, frameworks, and methodologies "
    "from a Job Description (JD). STRICTLY exclude soft skills such as communication, leadership, "
    "creativity, problem-solving, teamwork, adaptability, interpersonal skills, and similar. "
    "Do NOT hallucinate skills. Return only skills explicitly mentioned in the JD."
)


def extract_weighted_skills_from_jd(jd_text: str, job_role: str, model: str | None = None) -> dict[str, float]:
    """Extracts a dict of {skill: importance_weight} from a job description."""
    result: WeightedSkillList = call_structured(
        system=_WEIGHTED_SKILL_SYSTEM,
        user=(
            f"Extract all technical skills from the following Job Description and assign importance "
            f"weights based on the job role '{job_role}'. Weights range 0 (least important) to "
            f"1 (most important). Keep multi-word skills together.\n\nJD:\n{jd_text}"
        ),
        schema=WeightedSkillList,
        model=model,
    )
    # .strip() first: the model occasionally emits near-duplicate skill
    # entries that differ only in surrounding whitespace, which would
    # otherwise survive as two distinct dict keys after lowercasing alone.
    return {item.skill.strip().lower(): item.weight for item in result.skills}


_RESUME_WEIGHTED_SKILL_SYSTEM = (
    "You are an expert technical recruiter. Your task is to extract ONLY technical skills, "
    "tools, technologies, platforms, cloud services, databases, frameworks, and methodologies "
    "that this candidate's resume explicitly mentions. STRICTLY exclude soft skills such as "
    "communication, leadership, creativity, problem-solving, teamwork, adaptability. "
    "Do NOT hallucinate skills -- return only skills explicitly present in the resume text."
)


def extract_weighted_skills_from_resume(resume_text: str, model: str | None = None) -> dict[str, float]:
    """Extracts a dict of {skill: confidence_weight} from a resume -- round 2's

    medium-cost narrowing signal. Unlike `extract_weighted_skills_from_jd`, the
    weight here reflects how strongly the resume backs the skill up (repeated
    mentions, years of use) rather than importance to a role.
    """
    result: WeightedSkillList = call_structured(
        system=_RESUME_WEIGHTED_SKILL_SYSTEM,
        user=(
            "Extract all technical skills mentioned in the following resume, and assign each a "
            "weight from 0 (barely mentioned) to 1 (clearly demonstrated with real experience).\n\n"
            f"Resume:\n{resume_text}"
        ),
        schema=WeightedSkillList,
        model=model,
    )
    return {item.skill.strip().lower(): item.weight for item in result.skills}
