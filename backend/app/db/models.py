import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Resume(Base):
    """One uploaded resume, kept per job-seeker user so it doesn't need to be
    re-uploaded for every analysis -- the "resume library"."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)  # Supabase auth.users.id
    filename: Mapped[str] = mapped_column(String, nullable=False)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalysisReport(Base):
    """A saved job-seeker analysis result -- the "past ATS evaluation
    reports" a job seeker can revisit without re-running anything."""

    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    resume_id: Mapped[str | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    resume_filename: Mapped[str] = mapped_column(String, nullable=False)
    job_role: Mapped[str] = mapped_column(String, nullable=False)
    job_desc_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # full JobSeekerAnalysisResponse
    overall_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_based_ats_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecruitmentProject(Base):
    """One recruiter-owned hiring campaign (e.g. "AI Engineer") -- an
    isolated, reopenable workspace that candidates accumulate into across
    multiple batch runs, instead of one throwaway analysis."""

    __tablename__ = "recruitment_projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recruiter_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    job_role: Mapped[str] = mapped_column(String, nullable=False)
    job_desc_text: Mapped[str] = mapped_column(Text, nullable=False)
    num_vacancies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ProjectCandidate(Base):
    """One candidate's result within a RecruitmentProject -- mirrors
    CandidateResult's fields so the existing recruiter UI components can
    render historical data with no shape changes."""

    __tablename__ = "project_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("recruitment_projects.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    candidate_name: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    overall_fit_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_based_ats_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_requirements: Mapped[list] = mapped_column(JSON, default=list)
    missing_requirements: Mapped[list] = mapped_column(JSON, default=list)
    requirement_verdicts: Mapped[list] = mapped_column(JSON, default=list)
    provisional_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    round_reached: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
