import asyncio
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Callable
from uuid import uuid4

from app.config import settings
from app.core.app_logging import recruiter_logger, set_current_logger
from app.models.schemas import CandidateResult, RecruiterAnalysisResponse, RoundCandidateSummary, RoundSummary
from app.services.contact_extractor import extract_contact_info
from app.services.degree_extractor import extract_degrees
from app.services.document_loader import load_document
from app.services.exp_extractor import extract_experience
from app.services.matching import calculate_overall_fit_score
from app.services.rag_matching import (
    estimate_provisional_score,
    estimate_skill_match_score,
    index_document,
    match_resume_to_requirements,
)
from app.services.skill_extractor import extract_weighted_skills_from_jd, extract_weighted_skills_from_resume

_DEGREE_RANKING = {"diploma": 1, "associate": 2, "bachelor": 3, "master": 4, "phd": 5}

# Paces round 3's one big rubric-scoring Groq call per candidate to roughly
# one per recruiter_call_interval_seconds, so each call sees a close-to-fresh
# TPM window instead of stacking token usage from back-to-back candidates.
# Round 2's calls are much lighter (single skill-extraction request, no
# evidence/citation instructions) so they run at their own concurrency
# instead, relying on call_structured's existing 429 backoff.
_pacing_lock = threading.Lock()
_last_call_started_at = 0.0


def _wait_for_pacing_slot() -> None:
    global _last_call_started_at
    with _pacing_lock:
        remaining = settings.recruiter_call_interval_seconds - (time.monotonic() - _last_call_started_at)
        if remaining > 0:
            time.sleep(remaining)
        _last_call_started_at = time.monotonic()


def _check_eligibility(resume_degree: dict, jd_degree: dict, resume_exp: int, jd_exp: int) -> list[str]:
    reasons = []
    if jd_degree["highest"] and resume_degree["highest"]:
        if _DEGREE_RANKING[resume_degree["highest"]] < _DEGREE_RANKING[jd_degree["highest"]]:
            reasons.append("Degree requirement not met.")
    if resume_exp < jd_exp:
        reasons.append("Experience requirement not met.")
    return reasons


def _candidate_rank_key(c: CandidateResult) -> tuple[int, float]:
    """Round 1's dense-cosine screen, round 2's skill-vs-skill cosine, and
    round 3's LLM-verified rubric percentage are different methodologies on
    different scales -- comparing their raw numbers against each other isn't
    meaningful (a round-1-only cosine score can easily read higher than a
    fully-vetted round-3 candidate's rubric score without either number
    saying anything about who's actually the better fit). Ranks by how far a
    candidate got through the funnel first (candidates who were scrutinized
    more deeply always outrank those cut earlier, as a group), then by that
    round's own native score to order within the group.
    """
    if not c.eligible:
        return (-1, 0.0)
    if c.round_reached >= 3:
        return (3, c.skill_based_ats_score)
    if c.round_reached == 2:
        return (2, c.skill_match_score)
    if c.round_reached == 1:
        return (1, c.provisional_score)
    return (0, 0.0)


def rank_candidates(candidates: list[CandidateResult]) -> list[CandidateResult]:
    return sorted(candidates, key=_candidate_rank_key, reverse=True)


@dataclass
class _Candidate:
    """Carries a surviving candidate's data forward between rounds -- kept as
    a plain in-process object (never serialized) since job_store is in-memory
    only.
    """

    filename: str
    storage_key: str
    resume_text: str
    experience_years: int = 0
    provisional_score: float = 0.0
    skill_match_score: float = 0.0
    extracted_skills: dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineState:
    batch_id: str
    job_role: str
    job_desc_text: str
    jd_skill_weights: dict[str, float]
    total_weight: float
    num_vacancies: int | None
    original_eligible_count: int
    ineligible_results: list[CandidateResult] = field(default_factory=list)
    screened_out_round1: list[CandidateResult] = field(default_factory=list)
    screened_out_round2: list[CandidateResult] = field(default_factory=list)
    round1_survivors: list[_Candidate] = field(default_factory=list)
    round2_survivors: list[_Candidate] = field(default_factory=list)


def _round1_shortlist_size(num_eligible: int, num_vacancies: int | None) -> int:
    if num_vacancies and num_vacancies > 0:
        size = math.ceil(num_vacancies * settings.recruiter_round1_shortlist_multiplier)
    else:
        size = math.ceil(num_eligible * settings.recruiter_round1_shortlist_percent)
    return min(num_eligible, max(settings.recruiter_round1_shortlist_min, size))


def _round2_shortlist_size(original_eligible_count: int, num_round1_survivors: int, num_vacancies: int | None) -> int:
    if num_vacancies and num_vacancies > 0:
        size = math.ceil(num_vacancies * settings.recruiter_round2_shortlist_multiplier)
    else:
        size = math.ceil(original_eligible_count * settings.recruiter_round2_shortlist_percent)
    return min(num_round1_survivors, max(settings.recruiter_round2_shortlist_min, size))


def _prescreen_one_sync(
    batch_id: str,
    storage_key: str,
    filename: str,
    content: bytes,
    jd_skill_weights: dict[str, float],
    jd_degree: dict,
    jd_exp: int,
) -> dict:
    """Round 1: free, local-only screen -- no Groq calls. Loads the resume,
    checks hard eligibility (degree/experience), and for eligible candidates
    indexes it in Qdrant (reused by round 3 later -- never re-indexed) and
    computes a cheap dense-cosine provisional score.
    """
    resume_text = load_document(filename, content)
    recruiter_logger.debug("_prescreen_one_sync filename=%s raw_resume_text=%r", filename, resume_text)
    if not resume_text:
        return {"filename": filename, "eligible": False, "reasons": ["Could not read resume file."]}

    resume_degree = extract_degrees(resume_text)
    resume_exp = extract_experience(resume_text)
    reasons = _check_eligibility(resume_degree, jd_degree, resume_exp, jd_exp)

    if reasons:
        recruiter_logger.info("_prescreen_one_sync filename=%s INELIGIBLE reasons=%r", filename, reasons)
        return {"filename": filename, "eligible": False, "reasons": reasons, "experience_years": resume_exp}

    index_document(batch_id, storage_key, resume_text)
    provisional_score = estimate_provisional_score(batch_id, storage_key, jd_skill_weights)
    recruiter_logger.info(
        "_prescreen_one_sync filename=%s provisional_score=%.2f", filename, provisional_score
    )

    return {
        "filename": filename,
        "storage_key": storage_key,
        "eligible": True,
        "resume_text": resume_text,
        "experience_years": resume_exp,
        "provisional_score": provisional_score,
    }


async def run_round1(
    job_desc_text: str,
    job_role: str,
    resumes: list[tuple[str, bytes]],
    num_vacancies: int | None = None,
    on_candidate: Callable[[str, str, float | None, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[PipelineState, RoundSummary]:
    """Round 1: cheap, local, LLM-free prescreen of every candidate. Runs at
    high concurrency since nothing here touches Groq.

    `should_stop` is checked once per candidate, right before starting its
    work -- a stop request can't interrupt a candidate already mid-flight,
    but no new candidate starts once it's set. Anyone skipped this way is
    reported as not-yet-processed (eligible=False) rather than silently
    dropped, so the caller's candidate count always adds up.
    """
    set_current_logger(recruiter_logger)
    recruiter_logger.info("=== run_round1 START job_role=%r resume_count=%d ===", job_role, len(resumes))

    jd_degree = extract_degrees(job_desc_text)
    jd_exp = extract_experience(job_desc_text)
    jd_skill_weights = extract_weighted_skills_from_jd(job_desc_text, job_role)
    total_weight = sum(jd_skill_weights.values())
    batch_id = str(uuid4())
    recruiter_logger.debug(
        "run_round1 jd_degree=%r jd_exp=%r jd_skill_weights=%r", jd_degree, jd_exp, jd_skill_weights
    )

    def stopped() -> bool:
        return bool(should_stop and should_stop())

    def notify(filename: str, state: str, score: float | None, phase: str) -> None:
        if on_candidate:
            on_candidate(filename, state, score, phase)

    if total_weight == 0:
        state = PipelineState(
            batch_id=batch_id,
            job_role=job_role,
            job_desc_text=job_desc_text,
            jd_skill_weights=jd_skill_weights,
            total_weight=total_weight,
            num_vacancies=num_vacancies,
            original_eligible_count=0,
        )
        return state, RoundSummary(round=1, label="Free prescreen", candidates=[], advancing_count=0)

    prescreen_semaphore = asyncio.Semaphore(settings.recruiter_prescreen_concurrency)

    async def prescreen_one(index: int, filename: str, content: bytes) -> dict:
        storage_key = f"{index}_{filename}"
        async with prescreen_semaphore:
            if stopped():
                return {"filename": filename, "eligible": False, "reasons": ["Stopped before processing."]}
            notify(filename, "running", None, "round1")
            outcome = await asyncio.to_thread(
                _prescreen_one_sync, batch_id, storage_key, filename, content, jd_skill_weights, jd_degree, jd_exp
            )
            if not outcome["eligible"]:
                notify(filename, "done", 0.0, "done")
            return outcome

    prescreen_results = await asyncio.gather(
        *(prescreen_one(i, name, content) for i, (name, content) in enumerate(resumes))
    )

    ineligible_results = [
        CandidateResult(
            filename=r["filename"],
            eligible=False,
            reasons=r["reasons"],
            experience_years=r["experience_years"],
            round_reached=0,
        )
        for r in prescreen_results
        if not r["eligible"]
    ]
    eligible = [r for r in prescreen_results if r["eligible"]]
    eligible.sort(key=lambda r: r["provisional_score"], reverse=True)

    shortlist_size = _round1_shortlist_size(len(eligible), num_vacancies)
    round1_shortlist = eligible[:shortlist_size]
    round1_cut = eligible[shortlist_size:]

    screened_out_round1 = []
    for r in round1_cut:
        notify(r["filename"], "done", r["provisional_score"], "round1_cut")
        screened_out_round1.append(
            CandidateResult(
                filename=r["filename"],
                eligible=True,
                experience_years=r["experience_years"],
                provisional_score=r["provisional_score"],
                shortlisted=False,
                round_reached=1,
            )
        )

    round1_survivors = []
    for r in round1_shortlist:
        notify(r["filename"], "pending", r["provisional_score"], "round1")
        round1_survivors.append(
            _Candidate(
                filename=r["filename"],
                storage_key=r["storage_key"],
                resume_text=r["resume_text"],
                experience_years=r["experience_years"],
                provisional_score=r["provisional_score"],
            )
        )

    summary_candidates = [
        RoundCandidateSummary(filename=r["filename"], eligible=False, reasons=r["reasons"])
        for r in prescreen_results
        if not r["eligible"]
    ] + [
        RoundCandidateSummary(filename=c.filename, eligible=True, score=c.provisional_score, advancing=True)
        for c in round1_survivors
    ] + [
        RoundCandidateSummary(filename=r["filename"], eligible=True, score=r["provisional_score"], advancing=False)
        for r in round1_cut
    ]

    state = PipelineState(
        batch_id=batch_id,
        job_role=job_role,
        job_desc_text=job_desc_text,
        jd_skill_weights=jd_skill_weights,
        total_weight=total_weight,
        num_vacancies=num_vacancies,
        original_eligible_count=len(eligible),
        ineligible_results=ineligible_results,
        screened_out_round1=screened_out_round1,
        round1_survivors=round1_survivors,
    )
    summary = RoundSummary(
        round=1, label="Free prescreen", candidates=summary_candidates, advancing_count=len(round1_survivors)
    )
    recruiter_logger.info(
        "=== run_round1 END shortlist_size=%d advancing=%r cut=%r ineligible=%r ===",
        shortlist_size,
        [c.filename for c in round1_survivors],
        [r["filename"] for r in round1_cut],
        [r["filename"] for r in prescreen_results if not r["eligible"]],
    )
    return state, summary


def _skill_match_one_sync(jd_skill_weights: dict[str, float], resume_text: str) -> tuple[dict[str, float], float]:
    extracted_skills = extract_weighted_skills_from_resume(resume_text)
    score = estimate_skill_match_score(jd_skill_weights, extracted_skills)
    return extracted_skills, score


def _candidate_was_matched(candidate: _Candidate) -> bool:
    """True once round 2 has actually run for this candidate. Distinguishes
    a genuine 0% skill-match score from a candidate round 2 never reached
    because the job was stopped first -- both look like `skill_match_score
    == 0.0`, but only the extracted-skills dict tells them apart.
    """
    return bool(candidate.extracted_skills) or candidate.skill_match_score > 0


async def run_round2(
    state: PipelineState,
    on_candidate: Callable[[str, str, float | None, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[PipelineState, RoundSummary]:
    """Round 2: one Groq call per round-1 survivor to extract the resume's
    own skill list, then same-granularity skill-vs-skill cosine matching --
    a much cleaner signal than round 1's chunk comparison, at a fraction of
    round 3's cost since it's a single lightweight call per candidate.

    Same cooperative-stop contract as round 1: `should_stop` is checked once
    per candidate before it starts. A candidate skipped this way keeps its
    round-1 provisional score and is reported as having only reached round 1
    (see `_candidate_was_matched`), not silently mislabeled as "screened out
    by round 2" when round 2 never actually ran for it.
    """
    set_current_logger(recruiter_logger)
    recruiter_logger.info(
        "=== run_round2 START round1_survivor_count=%d ===", len(state.round1_survivors)
    )

    def stopped() -> bool:
        return bool(should_stop and should_stop())

    def notify(filename: str, state_: str, score: float | None, phase: str) -> None:
        if on_candidate:
            on_candidate(filename, state_, score, phase)

    match_semaphore = asyncio.Semaphore(settings.recruiter_round2_concurrency)

    async def match_one(candidate: _Candidate) -> _Candidate:
        async with match_semaphore:
            if stopped():
                return candidate
            notify(candidate.filename, "running", None, "round2")
            extracted_skills, score = await asyncio.to_thread(
                _skill_match_one_sync, state.jd_skill_weights, candidate.resume_text
            )
            candidate.extracted_skills = extracted_skills
            candidate.skill_match_score = score
            recruiter_logger.info(
                "run_round2 filename=%s extracted_skills=%r skill_match_score=%.2f",
                candidate.filename,
                extracted_skills,
                score,
            )
            return candidate

    matched = list(await asyncio.gather(*(match_one(c) for c in state.round1_survivors)))
    matched.sort(key=lambda c: c.skill_match_score, reverse=True)

    shortlist_size = _round2_shortlist_size(state.original_eligible_count, len(matched), state.num_vacancies)
    round2_shortlist = matched[:shortlist_size]
    round2_cut = matched[shortlist_size:]

    screened_out_round2 = []
    for c in round2_cut:
        if _candidate_was_matched(c):
            notify(c.filename, "done", c.skill_match_score, "round2_cut")
            screened_out_round2.append(
                CandidateResult(
                    filename=c.filename,
                    eligible=True,
                    experience_years=c.experience_years,
                    provisional_score=c.provisional_score,
                    skill_match_score=c.skill_match_score,
                    shortlisted=False,
                    round_reached=2,
                )
            )
        else:
            # Stopped before round 2 ever ran for this candidate -- report
            # them at round 1's own score, not a misleading round-2 cut.
            screened_out_round2.append(
                CandidateResult(
                    filename=c.filename,
                    eligible=True,
                    experience_years=c.experience_years,
                    provisional_score=c.provisional_score,
                    shortlisted=False,
                    round_reached=1,
                )
            )

    for c in round2_shortlist:
        notify(c.filename, "pending", c.skill_match_score, "round2")

    state.screened_out_round2 = screened_out_round2
    state.round2_survivors = round2_shortlist

    summary_candidates = [
        RoundCandidateSummary(filename=c.filename, eligible=True, score=c.skill_match_score, advancing=True)
        for c in round2_shortlist
    ] + [
        RoundCandidateSummary(filename=c.filename, eligible=True, score=c.skill_match_score, advancing=False)
        for c in round2_cut
    ]
    summary = RoundSummary(
        round=2,
        label="Skill-match narrowing",
        candidates=summary_candidates,
        advancing_count=len(round2_shortlist),
    )
    recruiter_logger.info(
        "=== run_round2 END advancing=%r cut=%r ===",
        [c.filename for c in round2_shortlist],
        [c.filename for c in round2_cut],
    )
    return state, summary


def _detailed_one_sync(
    batch_id: str,
    storage_key: str,
    filename: str,
    resume_text: str,
    experience_years: int,
    provisional_score: float,
    skill_match_score: float,
    jd_skill_weights: dict[str, float],
    total_weight: float,
    job_desc_text: str,
) -> CandidateResult:
    """Round 3: the expensive per-requirement LLM verification -- only for
    candidates that survived both prior cuts.
    """
    _wait_for_pacing_slot()
    rubric = match_resume_to_requirements(
        batch_id,
        storage_key,
        resume_text,
        jd_skill_weights,
        batch_size=settings.recruiter_rubric_batch_size,
        evidence_top_k=settings.recruiter_evidence_top_k,
        already_indexed=True,
    )
    overall_fit_score = calculate_overall_fit_score(resume_text, job_desc_text)
    contact = extract_contact_info(resume_text)

    satisfied_weight = sum(v.weight for v in rubric.verdicts if v.satisfied)
    normalized_score = (satisfied_weight / total_weight * 100) if total_weight > 0 else 0.0

    return CandidateResult(
        filename=filename,
        eligible=True,
        experience_years=experience_years,
        candidate_name=contact.name,
        candidate_email=contact.email,
        candidate_phone=contact.phone,
        overall_fit_score=overall_fit_score,
        skill_based_ats_score=normalized_score,
        matched_requirements=[v.requirement for v in rubric.verdicts if v.satisfied],
        missing_requirements=[v.requirement for v in rubric.verdicts if not v.satisfied],
        requirement_verdicts=rubric.verdicts,
        provisional_score=provisional_score,
        skill_match_score=skill_match_score,
        shortlisted=True,
        round_reached=3,
    )


async def run_round3(
    state: PipelineState,
    on_candidate: Callable[[str, str, float | None, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> RecruiterAnalysisResponse:
    """Round 3: expensive, evidence-grounded per-requirement LLM review,
    paced the same way the original single-round design was, run only on
    round 2's survivors.

    Same cooperative-stop contract: a candidate `should_stop` catches before
    its detailed review starts is reported at round 2's skill-match score
    instead, never silently dropped.
    """
    set_current_logger(recruiter_logger)
    recruiter_logger.info(
        "=== run_round3 START round2_survivor_count=%d ===", len(state.round2_survivors)
    )

    def stopped() -> bool:
        return bool(should_stop and should_stop())

    def notify(filename: str, state_: str, score: float | None, phase: str) -> None:
        if on_candidate:
            on_candidate(filename, state_, score, phase)

    detail_semaphore = asyncio.Semaphore(settings.recruiter_concurrency)

    async def detailed_one(candidate: _Candidate) -> CandidateResult:
        async with detail_semaphore:
            if stopped():
                return CandidateResult(
                    filename=candidate.filename,
                    eligible=True,
                    experience_years=candidate.experience_years,
                    provisional_score=candidate.provisional_score,
                    skill_match_score=candidate.skill_match_score,
                    shortlisted=False,
                    round_reached=2,
                )
            notify(candidate.filename, "running", None, "round3")
            result = await asyncio.to_thread(
                _detailed_one_sync,
                state.batch_id,
                candidate.storage_key,
                candidate.filename,
                candidate.resume_text,
                candidate.experience_years,
                candidate.provisional_score,
                candidate.skill_match_score,
                state.jd_skill_weights,
                state.total_weight,
                state.job_desc_text,
            )
            notify(candidate.filename, "done", result.skill_based_ats_score, "done")
            return result

    detailed_results = list(await asyncio.gather(*(detailed_one(c) for c in state.round2_survivors)))

    candidates = state.ineligible_results + state.screened_out_round1 + state.screened_out_round2 + detailed_results
    candidates = rank_candidates(candidates)

    recruiter_logger.info(
        "=== run_round3 END final_ranking=%r ===",
        [(c.filename, round(c.skill_based_ats_score, 1)) for c in candidates],
    )

    return RecruiterAnalysisResponse(
        job_role=state.job_role,
        total_candidates=len(candidates),
        ranked_candidates=candidates,
    )


def finalize_stopped_after_round1(state: PipelineState) -> RecruiterAnalysisResponse:
    """Builds the best-effort final result when a job is stopped while
    awaiting approval after round 1 (or mid-round 1). Every candidate in
    `round1_survivors` genuinely finished round 1 -- round1's own stop-check
    keeps anyone it skips out of that list entirely -- so no ambiguity here.
    """
    candidates = (
        list(state.ineligible_results)
        + list(state.screened_out_round1)
        + [
            CandidateResult(
                filename=c.filename,
                eligible=True,
                experience_years=c.experience_years,
                provisional_score=c.provisional_score,
                shortlisted=False,
                round_reached=1,
            )
            for c in state.round1_survivors
        ]
    )
    candidates = rank_candidates(candidates)
    return RecruiterAnalysisResponse(
        job_role=state.job_role, total_candidates=len(candidates), ranked_candidates=candidates
    )


def finalize_stopped_after_round2(state: PipelineState) -> RecruiterAnalysisResponse:
    """Builds the best-effort final result when a job is stopped while
    awaiting approval after round 2 (or mid-round 2). Unlike round 1's
    survivors, some of `round2_survivors` may not have actually been matched
    yet if the stop landed mid-round -- `_candidate_was_matched` tells them
    apart from genuine round-2 finishers.
    """
    def result_for(c: _Candidate) -> CandidateResult:
        if _candidate_was_matched(c):
            return CandidateResult(
                filename=c.filename,
                eligible=True,
                experience_years=c.experience_years,
                provisional_score=c.provisional_score,
                skill_match_score=c.skill_match_score,
                shortlisted=False,
                round_reached=2,
            )
        return CandidateResult(
            filename=c.filename,
            eligible=True,
            experience_years=c.experience_years,
            provisional_score=c.provisional_score,
            shortlisted=False,
            round_reached=1,
        )

    candidates = (
        list(state.ineligible_results)
        + list(state.screened_out_round1)
        + list(state.screened_out_round2)
        + [result_for(c) for c in state.round2_survivors]
    )
    candidates = rank_candidates(candidates)
    return RecruiterAnalysisResponse(
        job_role=state.job_role, total_candidates=len(candidates), ranked_candidates=candidates
    )
