from app.core.llm import call_structured
from app.models.schemas import FabricationCheck, OptimizedResume

_OPTIMIZE_SYSTEM = (
    "You are an expert resume writer and ATS optimization specialist. You improve wording, "
    "structure, technical specificity, and keyword coverage -- you NEVER invent or add skills, "
    "projects, certifications, employers, job titles, dates, or achievements that are not already "
    "present in the original resume. Every fact in your output must be traceable to the original "
    "text; you may only rephrase, reorganize, emphasize, or tighten it."
)


def generate_optimized_resume(resume_text: str, job_desc_text: str, model: str | None = None) -> OptimizedResume:
    """One structured rewrite pass, tailored to the target JD. Not yet
    guaranteed fact-safe on its own -- see `find_fabrications`/
    `correct_fabrications`, which verify and, if needed, patch this output
    before it's shown to the user.
    """
    return call_structured(
        system=_OPTIMIZE_SYSTEM,
        user=(
            "Rewrite the resume below into a polished, ATS-friendly version tailored to the target "
            "job description. Prioritize the skills, projects, and experience most relevant to the "
            "job description. Replace weak/generic verbs with stronger ones, improve technical "
            "specificity, and tighten sentences -- but do NOT add any fact (skill, tool, number, "
            "employer, title, certification) that isn't already present in the original resume "
            "text.\n\n"
            f"Job Description:\n{job_desc_text}\n\n"
            f"Original Resume:\n{resume_text}"
        ),
        schema=OptimizedResume,
        model=model,
        max_completion_tokens=2048,
    )


def _flatten(resume: OptimizedResume) -> str:
    parts = []
    if resume.full_name:
        parts.append(resume.full_name)
    if resume.contact_line:
        parts.append(resume.contact_line)
    for section in resume.sections:
        parts.append(section.heading)
        parts.extend(section.lines)
    return "\n".join(parts)


_FABRICATION_SYSTEM = (
    "You are a meticulous fact-checker comparing a rewritten resume against the original. You "
    "flag ONLY genuinely new claims -- a rephrased version of something already present is NOT a "
    "fabrication."
)


def find_fabrications(original_text: str, optimized: OptimizedResume, model: str | None = None) -> list[str]:
    """Deterministic-in-intent safety net, not a stylistic check: catches the
    one failure mode that actually matters here -- the rewrite inventing a
    skill, number, or credential the candidate never claimed.
    """
    result: FabricationCheck = call_structured(
        system=_FABRICATION_SYSTEM,
        user=(
            "Compare the OPTIMIZED resume text against the ORIGINAL resume text. List any skill, "
            "tool, technology, certification, job title, employer, or quantified achievement that "
            "appears in the OPTIMIZED text but is not genuinely present (even if reworded) in the "
            "ORIGINAL.\n\n"
            f"ORIGINAL:\n{original_text}\n\nOPTIMIZED:\n{_flatten(optimized)}"
        ),
        schema=FabricationCheck,
        model=model,
        max_completion_tokens=512,
    )
    return result.fabricated_claims


def correct_fabrications(
    optimized: OptimizedResume, fabricated_claims: list[str], model: str | None = None
) -> OptimizedResume:
    claims_block = "\n".join(f"- {c}" for c in fabricated_claims)
    return call_structured(
        system=_OPTIMIZE_SYSTEM,
        user=(
            "The resume below (as structured JSON) contains claims that are NOT genuinely "
            "supported by the candidate's original resume. Remove or rephrase ONLY these specific "
            "unsupported claims -- keep everything else in the resume exactly the same, same "
            "structure, same sections.\n\n"
            f"Unsupported claims to remove/fix:\n{claims_block}\n\n"
            f"Resume:\n{optimized.model_dump_json()}"
        ),
        schema=OptimizedResume,
        model=model,
        max_completion_tokens=2048,
    )


def optimize_and_verify(resume_text: str, job_desc_text: str, model: str | None = None) -> OptimizedResume:
    """The full pipeline: generate, verify against the original for
    fabricated facts, and patch once if the verification pass finds any.
    Only one correction round -- a rewrite that still fabricates after being
    told exactly what to fix is a model-quality problem, not something a
    retry loop should paper over.
    """
    optimized = generate_optimized_resume(resume_text, job_desc_text, model=model)
    fabricated = find_fabrications(resume_text, optimized, model=model)
    if fabricated:
        optimized = correct_fabrications(optimized, fabricated, model=model)
    return optimized
