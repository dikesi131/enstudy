from datetime import datetime, timedelta
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


PERIOD_DAYS = {
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
}

EBBINGHAUS_INTERVAL_DAYS = [1, 2, 4, 7, 15, 30, 60]


def normalize_word(word: str) -> str:
    return (word or "").strip().lower()


def fetch_word_profile(word: str) -> dict:
    normalized = normalize_word(word)
    if not normalized:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{normalized}"
    req = Request(url, headers={"User-Agent": "EnStudy/1.0"})
    try:
        with urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError):
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    if not isinstance(payload, list) or not payload:
        return {
            "phonetic": None,
            "part_of_speech": None,
            "meaning": None,
        }

    first = payload[0]
    phonetic = first.get("phonetic")
    if not phonetic:
        phonetics = first.get("phonetics") or []
        for item in phonetics:
            text = item.get("text")
            if text:
                phonetic = text
                break

    part_of_speech_items: list[str] = []
    meaning_items: list[str] = []
    meanings = first.get("meanings") or []
    for meaning_item in meanings:
        pos = meaning_item.get("partOfSpeech")
        if pos and pos not in part_of_speech_items:
            part_of_speech_items.append(pos)
        defs = meaning_item.get("definitions") or []
        for d in defs:
            definition = d.get("definition")
            if definition and definition not in meaning_items:
                meaning_items.append(definition)

    part_of_speech = part_of_speech_items[0] if part_of_speech_items else None
    meaning = meaning_items[0] if meaning_items else None

    return {
        "phonetic": phonetic,
        "part_of_speech": part_of_speech,
        "part_of_speech_items": part_of_speech_items,
        "meaning": meaning,
        "meaning_items": meaning_items,
    }


def _has_profile(profile: dict) -> bool:
    return bool(
        profile.get("phonetic")
        or profile.get("part_of_speech")
        or profile.get("meaning")
        or profile.get("part_of_speech_items")
        or profile.get("meaning_items")
    )


def get_latest_profile_by_word(db: Session, word: str) -> dict:
    row = (
        db.query(models.StudyEntry)
        .filter(models.StudyEntry.word == word)
        .order_by(models.StudyEntry.created_at.desc())
        .first()
    )
    if not row:
        return {"phonetic": None, "part_of_speech": None, "meaning": None}

    return {
        "phonetic": row.phonetic,
        "part_of_speech": row.part_of_speech,
        "part_of_speech_items": _parse_json_list(getattr(row, "part_of_speech_all", None), row.part_of_speech),
        "meaning": row.meaning,
        "meaning_items": _parse_json_list(getattr(row, "meaning_all", None), row.meaning),
    }


def _parse_json_list(raw_value, fallback_value) -> list[str]:
    if raw_value:
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    if fallback_value:
        return [str(fallback_value)]
    return []


def serialize_entry(row: models.StudyEntry) -> dict:
    part_items = _parse_json_list(getattr(row, "part_of_speech_all", None), getattr(row, "part_of_speech", None))
    meaning_items = _parse_json_list(getattr(row, "meaning_all", None), getattr(row, "meaning", None))

    next_review_at = getattr(row, "next_review_at", None)
    is_due = bool(next_review_at and next_review_at <= datetime.utcnow())

    return {
        "id": int(getattr(row, "id")),
        "word": getattr(row, "word"),
        "phonetic": getattr(row, "phonetic", None),
        "part_of_speech": getattr(row, "part_of_speech", None) or (part_items[0] if part_items else None),
        "part_of_speech_items": part_items,
        "meaning": getattr(row, "meaning", None) or (meaning_items[0] if meaning_items else None),
        "meaning_items": meaning_items,
        "sentence": getattr(row, "sentence"),
        "sentence_audio_path": getattr(row, "sentence_audio_path", None),
        "review_stage": int(getattr(row, "review_stage", 0) or 0),
        "last_reviewed_at": getattr(row, "last_reviewed_at", None),
        "next_review_at": next_review_at,
        "is_due": is_due,
        "created_at": getattr(row, "created_at"),
        "updated_at": getattr(row, "updated_at"),
    }


def _safe_review_stage(value) -> int:
    try:
        stage = int(value or 0)
    except (TypeError, ValueError):
        stage = 0
    return max(0, min(stage, len(EBBINGHAUS_INTERVAL_DAYS) - 1))


def _resolve_review_baseline(row: models.StudyEntry) -> datetime:
    baseline = getattr(row, "last_reviewed_at", None) or getattr(row, "created_at", None)
    return baseline or datetime.utcnow()


def _calculate_next_review_at(baseline: datetime, stage: int) -> datetime:
    return baseline + timedelta(days=EBBINGHAUS_INTERVAL_DAYS[_safe_review_stage(stage)])


def _ensure_review_schedule(row: models.StudyEntry) -> bool:
    changed = False
    stage = _safe_review_stage(getattr(row, "review_stage", 0))
    if getattr(row, "review_stage", 0) != stage:
        setattr(row, "review_stage", stage)
        changed = True

    if not getattr(row, "last_reviewed_at", None):
        setattr(row, "last_reviewed_at", _resolve_review_baseline(row))
        changed = True

    if not getattr(row, "next_review_at", None):
        baseline = _resolve_review_baseline(row)
        setattr(row, "next_review_at", _calculate_next_review_at(baseline, stage))
        changed = True

    return changed


def ensure_profile(db: Session, word: str, profile: dict | None = None) -> dict:
    candidate = profile or fetch_word_profile(word)
    if _has_profile(candidate):
        return candidate

    fallback = get_latest_profile_by_word(db, word)
    if _has_profile(fallback):
        return fallback

    raise ValueError(
        "无法从 Free Dictionary API 获取该单词的词性/释义，请检查网络或更换单词后重试。"
    )


def list_entries(db: Session, skip: int = 0, limit: int = 100, period: str = "weekly"):
    days = PERIOD_DAYS.get(period, 7)
    threshold = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.StudyEntry)
        .filter(models.StudyEntry.created_at >= threshold)
        .order_by(models.StudyEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_entry_by_word(db: Session, word: str):
    normalized = normalize_word(word)
    if not normalized:
        return None
    return (
        db.query(models.StudyEntry)
        .filter(func.lower(models.StudyEntry.word) == normalized)
        .order_by(models.StudyEntry.created_at.desc())
        .first()
    )


def create_entry(db: Session, payload: schemas.StudyEntryCreate):
    profile = ensure_profile(db, payload.word)
    now = datetime.utcnow()
    initial_stage = 0
    row = models.StudyEntry(
        word=payload.word.strip(),
        sentence=payload.sentence.strip(),
        phonetic=profile.get("phonetic"),
        part_of_speech=profile.get("part_of_speech"),
        part_of_speech_all=json.dumps(profile.get("part_of_speech_items") or []),
        meaning=profile.get("meaning"),
        meaning_all=json.dumps(profile.get("meaning_items") or []),
        review_stage=initial_stage,
        last_reviewed_at=now,
        next_review_at=_calculate_next_review_at(now, initial_stage),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_entry_with_profile(db: Session, payload: schemas.StudyEntryCreate, profile: dict):
    resolved = ensure_profile(db, payload.word, profile=profile)
    now = datetime.utcnow()
    initial_stage = 0
    row = models.StudyEntry(
        word=payload.word.strip(),
        sentence=payload.sentence.strip(),
        phonetic=resolved.get("phonetic"),
        part_of_speech=resolved.get("part_of_speech"),
        part_of_speech_all=json.dumps(resolved.get("part_of_speech_items") or []),
        meaning=resolved.get("meaning"),
        meaning_all=json.dumps(resolved.get("meaning_items") or []),
        review_stage=initial_stage,
        last_reviewed_at=now,
        next_review_at=_calculate_next_review_at(now, initial_stage),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_entry_basic(db: Session, payload: schemas.StudyEntryCreate):
    now = datetime.utcnow()
    initial_stage = 0
    row = models.StudyEntry(
        word=payload.word.strip(),
        sentence=payload.sentence.strip(),
        phonetic=None,
        part_of_speech=None,
        part_of_speech_all=json.dumps([]),
        meaning=None,
        meaning_all=json.dumps([]),
        review_stage=initial_stage,
        last_reviewed_at=now,
        next_review_at=_calculate_next_review_at(now, initial_stage),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_entry(db: Session, entry_id: int) -> bool:
    row = db.query(models.StudyEntry).filter(models.StudyEntry.id == entry_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_entry_by_id(db: Session, entry_id: int):
    return db.query(models.StudyEntry).filter(models.StudyEntry.id == entry_id).first()


def set_entry_sentence_audio_path(db: Session, entry_id: int, audio_path: str) -> None:
    row = get_entry_by_id(db, entry_id)
    if not row:
        return
    setattr(row, "sentence_audio_path", audio_path)
    db.add(row)
    db.commit()


def get_review_entries(db: Session, limit: int = 50):
    now = datetime.utcnow()
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    rows = db.query(models.StudyEntry).order_by(models.StudyEntry.created_at.desc()).all()
    changed = False
    due_today: list[models.StudyEntry] = []

    for row in rows:
        changed = _ensure_review_schedule(row) or changed
        next_review_at = getattr(row, "next_review_at", None)
        if not next_review_at:
            continue
        if next_review_at <= end_of_today:
            due_today.append(row)

    due_today.sort(key=lambda r: getattr(r, "next_review_at", end_of_today))

    if changed:
        db.commit()

    return due_today[:limit]


def _next_stage_by_outcome(current_stage: int, outcome: str) -> int:
    max_stage = len(EBBINGHAUS_INTERVAL_DAYS) - 1
    if outcome == "remembered":
        return min(current_stage + 2, max_stage)
    if outcome == "fuzzy":
        return min(current_stage + 1, max_stage)
    if outcome == "forgot":
        return 0
    return min(current_stage + 1, max_stage)


def mark_entry_reviewed(db: Session, entry_id: int, outcome: str = "fuzzy"):
    row = get_entry_by_id(db, entry_id)
    if not row:
        return None

    _ensure_review_schedule(row)
    current_stage = _safe_review_stage(getattr(row, "review_stage", 0))
    next_stage = _next_stage_by_outcome(current_stage, outcome)
    now = datetime.utcnow()

    setattr(row, "review_stage", next_stage)
    setattr(row, "last_reviewed_at", now)
    setattr(row, "next_review_at", _calculate_next_review_at(now, next_stage))

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _bucket_key_week(dt: datetime):
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _bucket_key_month(dt: datetime):
    return f"{dt.year}-{dt.month:02d}"


def get_unified_stats(db: Session):
    now = datetime.utcnow()
    t7 = now - timedelta(days=7)
    t30 = now - timedelta(days=30)
    t365 = now - timedelta(days=365)

    total_items = db.query(func.count(models.StudyEntry.id)).scalar() or 0
    items_last_7_days = (
        db.query(func.count(models.StudyEntry.id)).filter(models.StudyEntry.created_at >= t7).scalar() or 0
    )
    items_last_30_days = (
        db.query(func.count(models.StudyEntry.id)).filter(models.StudyEntry.created_at >= t30).scalar() or 0
    )
    items_last_365_days = (
        db.query(func.count(models.StudyEntry.id)).filter(models.StudyEntry.created_at >= t365).scalar() or 0
    )

    recent = db.query(models.StudyEntry.created_at).filter(models.StudyEntry.created_at >= t365).all()
    weekly: dict[str, int] = {}
    monthly: dict[str, int] = {}
    for (created_at,) in recent:
        dt = created_at
        w = _bucket_key_week(dt)
        m = _bucket_key_month(dt)
        weekly[w] = weekly.get(w, 0) + 1
        monthly[m] = monthly.get(m, 0) + 1

    weekly_points = [{"label": k, "count": weekly[k]} for k in sorted(weekly.keys())][-12:]
    monthly_points = [{"label": k, "count": monthly[k]} for k in sorted(monthly.keys())][-12:]

    return {
        "total_items": total_items,
        "items_last_7_days": items_last_7_days,
        "items_last_30_days": items_last_30_days,
        "items_last_365_days": items_last_365_days,
        "weekly_trend": weekly_points,
        "monthly_trend": monthly_points,
    }
