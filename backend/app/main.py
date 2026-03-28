from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.config import settings
from app.database import Base, engine
from app.routers import audio, entries, io_ops, review, stats

Base.metadata.create_all(bind=engine)


def ensure_schema_updates() -> None:
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("study_entries")}
    if "sentence_audio_path" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN sentence_audio_path VARCHAR(512) NULL"))
    if "part_of_speech_all" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN part_of_speech_all TEXT NULL"))
    if "meaning_all" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN meaning_all TEXT NULL"))
    if "review_stage" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN review_stage INTEGER NOT NULL DEFAULT 0"))
    if "last_reviewed_at" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN last_reviewed_at DATETIME NULL"))
    if "next_review_at" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE study_entries ADD COLUMN next_review_at DATETIME NULL"))


ensure_schema_updates()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entries.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(io_ops.router, prefix="/api")
app.include_router(audio.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
