from typing import Callable
from uuid import uuid4

from app.core.app_logging import job_seeker_logger, set_current_logger
from app.core.llm import call_llm
from app.core.vector_store import delete_document
from app.models.schemas import (
    DegreeInfo,
    EligibilityResult,
    JobSeekerAnalysisResponse,
    RequirementVerdict,
)
from app.services.degree_extractor import extract_degrees
from app.services.exp_extractor import extract_experience
from app.services.matching import calculate_overall_fit_score
from app.services.rag_matching import match_resume_to_requirements
from app.services.resume_optimizer import optimize_and_verify
from app.services.skill_extractor import extract_weighted_skills_from_jd

_DEGREE_RANKING = {"diploma": 1, "associate": 2, "bachelor": 3, "master": 4, "phd": 5}

_COVER_LETTER_PROMPT = """Write a professional, 3-paragraph cover letter based on the resume and job description.
Highlight relevant skills, experiences, and motivation.

Resume: {resume_text}
Job Description: {job_desc_text}
"""


def _check_eligibility(resume_degree: dict, jd_degree: dict, resume_exp: int, jd_exp: int) -> EligibilityResult:
    reasons = []
    if jd_degree["highest"] and resume_degree["highest"]:
        if _DEGREE_RANKING[resume_degree["highest"]] < _DEGREE_RANKING[jd_degree["highest"]]:
            reasons.append("Degree requirement not met.")
    if resume_exp < jd_exp:
        reasons.append("Experience requirement not met.")
    return EligibilityResult(eligible=not reasons, reasons=reasons)


def analyze_job_seeker(
    resume_text: str,
    job_desc_text: str,
    job_role: str,
    on_stage: Callable[[str, str], None] | None = None,
    on_partial: Callable[..., None] | None = None,
    on_activity: Callable[[str], None] | None = None,
    on_verdict: Callable[[RequirementVerdict], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> JobSeekerAnalysisResponse:
    set_current_logger(job_seeker_logger)
    job_seeker_logger.info("=== analyze_job_seeker START job_role=%r ===", job_role)
    job_seeker_logger.debug("analyze_job_seeker raw_resume_text=%r", resume_text)
    job_seeker_logger.debug("analyze_job_seeker raw_job_desc_text=%r", job_desc_text)

    def notify(stage: str, state: str) -> None:
        if on_stage:
            on_stage(stage, state)

    def publish(**fields) -> None:
        if on_partial:
            on_partial(**fields)

    notify("eligibility", "running")
    resume_degree = extract_degrees(resume_text)
    jd_degree = extract_degrees(job_desc_text)
    resume_exp = extract_experience(resume_text)
    jd_exp = extract_experience(job_desc_text)
    job_seeker_logger.debug(
        "analyze_job_seeker resume_degree=%r jd_degree=%r resume_exp=%r jd_exp=%r",
        resume_degree,
        jd_degree,
        resume_exp,
        jd_exp,
    )

    eligibility = _check_eligibility(resume_degree, jd_degree, resume_exp, jd_exp)

    resume_degree_info = DegreeInfo(all_degrees=resume_degree["all"], highest=resume_degree["highest"])
    jd_degree_info = DegreeInfo(all_degrees=jd_degree["all"], highest=jd_degree["highest"])
    publish(
        resume_experience_years=resume_exp,
        jd_experience_years=jd_exp,
        resume_degree=resume_degree_info.model_dump(),
        jd_degree=jd_degree_info.model_dump(),
        eligibility=eligibility.model_dump(),
    )
    notify("eligibility", "done")

    if not eligibility.eligible:
        return JobSeekerAnalysisResponse(
            eligibility=eligibility,
            resume_degree=resume_degree_info,
            jd_degree=jd_degree_info,
            resume_experience_years=resume_exp,
            jd_experience_years=jd_exp,
        )

    # A job seeker's resume is only ever meant for this one analysis --
    # index it under a throwaway batch_id and delete it from Qdrant once done.
    batch_id = str(uuid4())
    filename = "resume"

    notify("requirements", "running")
    jd_skill_weights = extract_weighted_skills_from_jd(job_desc_text, job_role)
    job_seeker_logger.debug("analyze_job_seeker jd_skill_weights=%r", jd_skill_weights)
    publish(jd_requirements=[{"requirement": k, "weight": v} for k, v in jd_skill_weights.items()])
    notify("requirements", "done")

    try:
        rubric = match_resume_to_requirements(
            batch_id,
            filename,
            resume_text,
            jd_skill_weights,
            on_stage=on_stage,
            on_activity=on_activity,
            on_verdict=on_verdict,
            should_stop=should_stop,
        )
    finally:
        delete_document(batch_id, filename)

    overall_fit_score = calculate_overall_fit_score(resume_text, job_desc_text)

    total_weight = sum(jd_skill_weights.values())
    satisfied_weight = sum(v.weight for v in rubric.verdicts if v.satisfied)
    normalized_score = (satisfied_weight / total_weight * 100) if total_weight > 0 else 0.0

    matched_requirements = [v.requirement for v in rubric.verdicts if v.satisfied]
    missing_requirements = [v.requirement for v in rubric.verdicts if not v.satisfied]

    # Cover letter and improvements are separate Groq calls after rubric
    # scoring -- if stop was requested mid-rubric, skip them too rather than
    # starting fresh work after the user already asked to stop.
    cover_letter = None
    optimized_resume = None
    if not (should_stop and should_stop()):
        notify("cover_letter", "running")
        cover_letter = call_llm(
            system="You are an expert career writing assistant.",
            user=_COVER_LETTER_PROMPT.format(resume_text=resume_text, job_desc_text=job_desc_text),
        )
        publish(cover_letter=cover_letter)
        notify("cover_letter", "done")

        notify("improvements", "running")
        optimized_resume = optimize_and_verify(resume_text, job_desc_text)
        publish(optimized_resume=optimized_resume)
        notify("improvements", "done")

    job_seeker_logger.info(
        "=== analyze_job_seeker END overall_fit_score=%.1f skill_based_ats_score=%.1f matched=%d missing=%d ===",
        overall_fit_score,
        normalized_score,
        len(matched_requirements),
        len(missing_requirements),
    )

    return JobSeekerAnalysisResponse(
        eligibility=eligibility,
        resume_degree=resume_degree_info,
        jd_degree=jd_degree_info,
        resume_experience_years=resume_exp,
        jd_experience_years=jd_exp,
        overall_fit_score=overall_fit_score,
        skill_based_ats_score=normalized_score,
        requirement_verdicts=rubric.verdicts,
        matched_requirements=matched_requirements,
        missing_requirements=missing_requirements,
        cover_letter=cover_letter,
        optimized_resume=optimized_resume,
    )
