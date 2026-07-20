import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.db import crud
from app.db.session import get_db_session
from app.models.schemas import CandidateStatus, JobStatusResponse, RecruiterAnalysisResponse, StageStatus
from app.services import job_store
from app.services.document_loader import load_document
from app.services.email_service import EmailNotConfiguredError, send_email
from app.services.job_store import JobState, StepState
from app.services.recruiter_service import (
    PipelineState,
    finalize_stopped_after_round1,
    finalize_stopped_after_round2,
    rank_candidates,
    run_round1,
    run_round2,
    run_round3,
)

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])


def _persist_candidates(project_id: str | None, result: RecruiterAnalysisResponse) -> None:
    if not project_id:
        return
    db = get_db_session()
    try:
        crud.save_project_candidates(db, project_id, result.ranked_candidates)
    finally:
        db.close()


def _candidate_callback(job_id: str):
    def on_candidate(filename: str, state: str, score: float | None, phase: str) -> None:
        job_store.update_candidate(job_id, filename, StepState(state), score, phase)

    return on_candidate


def _stop_check(job_id: str):
    return lambda: job_store.is_stop_requested(job_id)


async def _run_round1_job(
    job_id: str, jd_text: str, job_role: str, resumes: list[tuple[str, bytes]], num_vacancies: int | None
) -> None:
    job_store.set_running(job_id)
    project_id = job_store.get_job(job_id).project_id
    try:
        state, summary = await run_round1(
            jd_text, job_role, resumes, num_vacancies, _candidate_callback(job_id), _stop_check(job_id)
        )
        if job_store.is_stop_requested(job_id):
            result = finalize_stopped_after_round1(state)
            job_store.set_stopped(job_id, result)
            _persist_candidates(project_id, result)
        elif summary.advancing_count == 0:
            # Nobody eligible, or the JD had no extractable skills -- nothing
            # to approve into round 2, so just finish with round 1's results.
            candidates = rank_candidates(state.ineligible_results + state.screened_out_round1)
            result = RecruiterAnalysisResponse(job_role=job_role, total_candidates=len(candidates), ranked_candidates=candidates)
            job_store.set_result(job_id, result)
            _persist_candidates(project_id, result)
        else:
            job_store.set_awaiting_approval(job_id, next_round=2, pipeline_state=state, pending_approval=summary)
    except Exception as e:
        job_store.set_error(job_id, str(e))


async def _run_round2_job(job_id: str, state: PipelineState) -> None:
    job_store.set_running(job_id)
    project_id = job_store.get_job(job_id).project_id
    try:
        state, summary = await run_round2(state, _candidate_callback(job_id), _stop_check(job_id))
        if job_store.is_stop_requested(job_id):
            result = finalize_stopped_after_round2(state)
            job_store.set_stopped(job_id, result)
            _persist_candidates(project_id, result)
        elif summary.advancing_count == 0:
            candidates = rank_candidates(
                state.ineligible_results + state.screened_out_round1 + state.screened_out_round2
            )
            result = RecruiterAnalysisResponse(
                job_role=state.job_role, total_candidates=len(candidates), ranked_candidates=candidates
            )
            job_store.set_result(job_id, result)
            _persist_candidates(project_id, result)
        else:
            job_store.set_awaiting_approval(job_id, next_round=3, pipeline_state=state, pending_approval=summary)
    except Exception as e:
        job_store.set_error(job_id, str(e))


async def _run_round3_job(job_id: str, state: PipelineState) -> None:
    job_store.set_running(job_id)
    project_id = job_store.get_job(job_id).project_id
    try:
        result = await run_round3(state, _candidate_callback(job_id), _stop_check(job_id))
        if job_store.is_stop_requested(job_id):
            job_store.set_stopped(job_id, result)
        else:
            job_store.set_result(job_id, result)
        _persist_candidates(project_id, result)
    except Exception as e:
        job_store.set_error(job_id, str(e))


@router.post("/projects")
async def create_project(
    name: str = Form(...),
    job_role: str = Form(...),
    job_description: UploadFile = File(...),
    num_vacancies: int | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    jd_bytes = await job_description.read()
    jd_text = load_document(job_description.filename or "", jd_bytes)
    if not name.strip() or not jd_text:
        raise HTTPException(status_code=400, detail="Project name and a readable job description are required.")

    db = get_db_session()
    try:
        project = crud.create_project(db, user.id, name.strip(), job_role, jd_text, num_vacancies)
        return {"id": project.id, "name": project.name}
    finally:
        db.close()


@router.get("/projects")
async def list_projects(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    db = get_db_session()
    try:
        projects = crud.list_projects(db, user.id)
        result = []
        for p in projects:
            candidate_count = len(crud.list_project_candidates(db, p.id))
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "job_role": p.job_role,
                    "num_vacancies": p.num_vacancies,
                    "candidate_count": candidate_count,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
            )
        return result
    finally:
        db.close()


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    db = get_db_session()
    try:
        project = crud.get_project(db, user.id, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        candidates = crud.list_project_candidates(db, project_id)
        return {
            "id": project.id,
            "name": project.name,
            "job_role": project.job_role,
            "job_desc_text": project.job_desc_text,
            "num_vacancies": project.num_vacancies,
            "candidates": [
                {
                    "filename": c.filename,
                    "eligible": c.eligible,
                    "reasons": c.reasons,
                    "experience_years": c.experience_years,
                    "candidate_name": c.candidate_name,
                    "candidate_email": c.candidate_email,
                    "candidate_phone": c.candidate_phone,
                    "overall_fit_score": c.overall_fit_score,
                    "skill_based_ats_score": c.skill_based_ats_score,
                    "matched_requirements": c.matched_requirements,
                    "missing_requirements": c.missing_requirements,
                    "requirement_verdicts": c.requirement_verdicts,
                    "provisional_score": c.provisional_score,
                    "skill_match_score": c.skill_match_score,
                    "shortlisted": c.shortlisted,
                    "round_reached": c.round_reached,
                }
                for c in candidates
            ],
        }
    finally:
        db.close()


@router.post("/projects/{project_id}/jobs")
async def create_job(
    project_id: str,
    background_tasks: BackgroundTasks,
    resumes: list[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    db = get_db_session()
    try:
        project = crud.get_project(db, user.id, project_id)
    finally:
        db.close()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    resume_payload = [(r.filename or "", await r.read()) for r in resumes]
    candidate_names = [name for name, _ in resume_payload]

    job = job_store.create_job("recruiter", candidate_names=candidate_names, project_id=project_id)
    background_tasks.add_task(
        _run_round1_job, job.id, project.job_desc_text, project.job_role, resume_payload, project.num_vacancies
    )
    return {"job_id": job.id}


@router.post("/jobs/{job_id}/approve")
async def approve_next_round(job_id: str, background_tasks: BackgroundTasks) -> dict:
    """Advances a paused job into its next round. The job only ever pauses
    here -- nothing after round 1 runs without an explicit approval call.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.state != JobState.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Job is not awaiting approval.")

    next_round, state = job_store.take_pipeline_state(job_id)
    if state is None:
        raise HTTPException(status_code=400, detail="No paused round state found.")

    if next_round == 2:
        background_tasks.add_task(_run_round2_job, job_id, state)
    elif next_round == 3:
        background_tasks.add_task(_run_round3_job, job_id, state)
    else:
        raise HTTPException(status_code=400, detail="Unexpected round to resume.")

    return {"status": "resumed", "round": next_round}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str) -> dict:
    """Requests the job stop at its next checkpoint (before the next
    candidate or batch starts). Whatever's already in flight finishes;
    nothing new starts after that.

    A job paused awaiting approval has no active loop to notice a flag --
    there's no round running to check it -- so that case finalizes
    immediately using the already-computed pipeline state instead.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.state == JobState.AWAITING_APPROVAL:
        next_round, state = job_store.take_pipeline_state(job_id)
        if state is not None:
            if next_round == 2:
                job_store.set_stopped(job_id, finalize_stopped_after_round1(state))
            elif next_round == 3:
                job_store.set_stopped(job_id, finalize_stopped_after_round2(state))
        return {"status": "stopped"}

    if not job_store.request_stop(job_id):
        raise HTTPException(status_code=400, detail="Job already finished.")
    return {"status": "stopping"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatusResponse(
        job_id=job.id,
        kind=job.kind,
        state=job.state.value,
        stages=[StageStatus(key=s.key, label=s.label, state=s.state.value) for s in job.stages],
        candidates=[
            CandidateStatus(filename=c.filename, state=c.state.value, score=c.score, phase=c.phase)
            for c in job.candidates
        ],
        pending_approval=job.pending_approval,
        result=job.result,
        error=job.error,
    )


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str


@router.post("/send-email")
async def send_candidate_email(payload: SendEmailRequest) -> dict:
    if not _EMAIL_RE.match(payload.to_email):
        raise HTTPException(status_code=400, detail="Invalid recipient email address.")
    if not payload.subject.strip() or not payload.body.strip():
        raise HTTPException(status_code=400, detail="Subject and body are required.")

    try:
        send_email(payload.to_email, payload.subject, payload.body)
    except EmailNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send email: {e}")

    return {"status": "sent"}
