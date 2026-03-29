from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class StudyEntry(Base):
    __tablename__ = "study_entries"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), nullable=False, index=True)
    phonetic = Column(String(255), nullable=True)
    part_of_speech = Column(String(100), nullable=True)
    part_of_speech_all = Column(Text, nullable=True)
    meaning = Column(Text, nullable=True)
    meaning_all = Column(Text, nullable=True)
    sentence = Column(Text, nullable=False)
    sentence_audio_path = Column(String(512), nullable=True)
    review_stage = Column(Integer, nullable=False, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, nullable=False, index=True)
    outcome = Column(String(32), nullable=False)
    reviewed_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
