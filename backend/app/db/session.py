from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Supabase's Postgres, connected to directly (not through PostgREST) -- our
# backend owns the schema for these tables via SQLAlchemy, separate from
# anything Supabase's own dashboard manages. Ownership checks happen in
# application code (see app/core/auth.py) rather than relying on Postgres
# Row-Level Security, since a direct connection doesn't carry the
# per-request JWT claims RLS needs to enforce itself.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    return SessionLocal()
