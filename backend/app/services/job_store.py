import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class StepState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"


@dataclass
class StageProgress:
    key: str
    label: str
    state: StepState = StepState.PENDING


@dataclass
class CandidateProgress:
    filename: str
    state: StepState = StepState.PENDING
    score: float | None = None
    phase: str = "pending"  # pending | screening | screened_out | detailed | done


@dataclass
class Job:
    id: str
    kind: str  # "job_seeker" | "recruiter"
    state: JobState = JobState.QUEUED
    stages: list[StageProgress] = field(default_factory=list)
    candidates: list[CandidateProgress] = field(default_factory=list)
    # Incremental job-seeker data, populated as each stage actually finishes
    # computing something, so the UI can show real results long before the
    # whole analysis completes instead of a bare progress tick.
    partial: dict[str, Any] = field(default_factory=dict)
    verdicts: list[Any] = field(default_factory=list)  # RequirementVerdict, appended as each resolves
    current_activity: str | None = None  # e.g. "Checking: power bi"
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    # Recruiter 3-round funnel: while state == AWAITING_APPROVAL, the job is
    # paused between rounds. `pending_approval` (a RoundSummary, kept as a
    # plain object here since job_store has no schema dependency) is what the
    # UI shows the recruiter; `pipeline_state` is the opaque, in-process data
    # (resume text, batch_id, extracted skills, etc.) `approve_next_round`
    # needs to resume exactly where round N left off. `next_round` records
    # which round (2 or 3) an approval should trigger.
    pending_approval: Any = None
    pipeline_state: Any = None
    next_round: int | None = None
    # Cooperative stop: a Groq call already in flight can't be killed
    # mid-request, so this is checked between units of work (each candidate,
    # each rubric batch) rather than actually interrupting one. Whatever's
    # already done stays; whatever hasn't started yet never starts.
    stop_requested: bool = False
    # Recruiter jobs are always scoped to a persistent RecruitmentProject --
    # carried on the in-memory Job itself so route handlers can persist final
    # candidates without threading project_id through PipelineState/
    # recruiter_service (which stay DB-agnostic).
    project_id: str | None = None


# In-memory only -- fine for a single-process personal project; jobs are
# lost on restart, which is an acceptable trade-off here.
_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job(
    kind: str,
    stage_defs: list[tuple[str, str]] | None = None,
    candidate_names: list[str] | None = None,
    project_id: str | None = None,
) -> Job:
    job = Job(id=str(uuid4()), kind=kind, project_id=project_id)
    if stage_defs:
        job.stages = [StageProgress(key=k, label=label) for k, label in stage_defs]
    if candidate_names:
        job.candidates = [CandidateProgress(filename=name) for name in candidate_names]
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def set_running(job_id: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.state = JobState.RUNNING


def update_stage(job_id: str, stage_key: str, state: StepState) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for stage in job.stages:
            if stage.key == stage_key:
                stage.state = state


def update_partial(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.partial.update(fields)


def append_verdict(job_id: str, verdict: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.verdicts.append(verdict)


def set_activity(job_id: str, text: str | None) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.current_activity = text


def update_candidate(
    job_id: str, filename: str, state: StepState, score: float | None = None, phase: str | None = None
) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for candidate in job.candidates:
            if candidate.filename == filename:
                candidate.state = state
                if score is not None:
                    candidate.score = score
                if phase is not None:
                    candidate.phase = phase


def set_result(job_id: str, result: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.result = result
            job.state = JobState.COMPLETED
            job.pending_approval = None
            job.pipeline_state = None
            job.next_round = None


def set_error(job_id: str, error: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.error = error
            job.state = JobState.FAILED


def set_awaiting_approval(job_id: str, next_round: int, pipeline_state: Any, pending_approval: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.state = JobState.AWAITING_APPROVAL
            job.next_round = next_round
            job.pipeline_state = pipeline_state
            job.pending_approval = pending_approval


def request_stop(job_id: str) -> bool:
    """Marks a job to stop at the next checkpoint. Returns False if the job
    doesn't exist or is already in a terminal state (nothing to stop).
    """
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        if job.state in (JobState.COMPLETED, JobState.FAILED, JobState.STOPPED):
            return False
        job.stop_requested = True
        return True


def is_stop_requested(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.stop_requested)


def set_stopped(job_id: str, result: Any = None) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job.result = result
            job.state = JobState.STOPPED
            job.pending_approval = None
            job.pipeline_state = None
            job.next_round = None


def take_pipeline_state(job_id: str) -> tuple[int | None, Any]:
    """Reads and clears the paused round's state -- called once by the
    /approve endpoint when resuming, so a job can't be accidentally resumed
    twice concurrently from the same paused state.
    """
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None, None
        next_round, pipeline_state = job.next_round, job.pipeline_state
        job.next_round = None
        job.pipeline_state = None
        return next_round, pipeline_state
