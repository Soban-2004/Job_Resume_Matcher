from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import job_seeker, recruiter
from app.db.models import Base
from app.db.session import engine

app = FastAPI(title="AI Resume & Job Matcher API", version="0.1.0")

# create_all only ever adds missing tables -- never touches existing ones --
# so this is safe to run on every startup instead of hand-rolling migrations
# for a schema that's still taking shape.
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_seeker.router)
app.include_router(recruiter.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
