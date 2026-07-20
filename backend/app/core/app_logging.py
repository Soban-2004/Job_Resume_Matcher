import contextvars
import logging
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)


def _make_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_DIR / filename, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


# Separate files per pipeline, per the ask -- job-seeker and recruiter runs
# should never be interleaved in the same log when diagnosing an issue.
job_seeker_logger = _make_logger("job_seeker", "job_seeker.log")
recruiter_logger = _make_logger("recruiter", "recruiter.log")

# rag_matching.py is shared by both pipelines. Rather than threading a
# `logger` parameter through every function signature (match_resume_to_
# requirements -> retrieve_evidence -> evaluate_rubric -> _evaluate_rubric_
# batch -> _suggest_certifications), each pipeline sets this contextvar once
# at its entry point; asyncio.to_thread propagates the current context into
# the worker thread, so deep shared functions just call get_logger() and
# automatically write to whichever pipeline's file is actually running --
# no signature changes needed anywhere in the RAG pipeline itself.
_current_logger: contextvars.ContextVar[logging.Logger] = contextvars.ContextVar(
    "current_logger", default=logging.getLogger("rag_unset")
)


def set_current_logger(logger: logging.Logger) -> None:
    _current_logger.set(logger)


def get_logger() -> logging.Logger:
    return _current_logger.get()
