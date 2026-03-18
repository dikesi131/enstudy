from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SentenceTTSRequest(BaseModel):
    text: Optional[str] = None
    entry_id: Optional[int] = None


class StudyEntryCreate(BaseModel):
    word: str = Field(min_length=1, max_length=255)
    sentence: str = Field(min_length=1)


class StudyEntryRead(BaseModel):
    id: int
    word: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    part_of_speech_items: list[str] = []
    meaning: Optional[str] = None
    meaning_items: list[str] = []
    sentence: str
    sentence_audio_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UnifiedImportRow(BaseModel):
    word: str
    sentence: str


class UnifiedImportPayload(BaseModel):
    items: list[UnifiedImportRow] = []


class ReviewUnifiedResponse(BaseModel):
    period: str
    items: list[StudyEntryRead]


class TrendPoint(BaseModel):
    label: str
    count: int


class StatsUnifiedOverview(BaseModel):
    total_items: int
    items_last_7_days: int
    items_last_30_days: int
    items_last_365_days: int
    weekly_trend: list[TrendPoint]
    monthly_trend: list[TrendPoint]
