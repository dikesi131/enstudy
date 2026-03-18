import csv
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db

router = APIRouter(prefix="/io", tags=["import-export"])


@router.get("/export")
def export_data(db: Session = Depends(get_db)):
    entries = db.query(models.StudyEntry).order_by(models.StudyEntry.id.asc()).all()

    payload = {
        "items": [crud.serialize_entry(i) for i in entries],
    }
    return JSONResponse(content=jsonable_encoder(payload))


@router.post("/import")
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()

    if file.filename and file.filename.lower().endswith(".json"):
        return _import_json(raw, db)

    if file.filename and file.filename.lower().endswith(".csv"):
        return _import_csv(raw, db)

    raise HTTPException(status_code=400, detail="Only .json or .csv file is supported")


def _import_json(raw: bytes, db: Session):
    try:
        payload = schemas.UnifiedImportPayload.model_validate(json.loads(raw.decode("utf-8")))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    imported_items = 0
    skipped_items = 0
    skipped_words: list[str] = []
    seen_words: set[str] = set()

    for item in payload.items:
        normalized = crud.normalize_word(item.word)
        if not normalized:
            continue
        if normalized in seen_words:
            skipped_items += 1
            skipped_words.append(item.word)
            continue
        seen_words.add(normalized)

        if crud.get_entry_by_word(db, item.word):
            skipped_items += 1
            skipped_words.append(item.word)
            continue

        profile = crud.fetch_word_profile(item.word)
        try:
            crud.create_entry_with_profile(
                db,
                schemas.StudyEntryCreate(word=item.word, sentence=item.sentence),
                profile,
            )
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"{item.word}: {exc}") from exc
        imported_items += 1

    return {
        "ok": True,
        "imported_items": imported_items,
        "skipped_items": skipped_items,
        "skipped_words": skipped_words,
    }


def _import_csv(raw: bytes, db: Session):
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])

    imported_items = 0
    skipped_items = 0
    skipped_words: list[str] = []
    seen_words: set[str] = set()

    if {"word", "sentence"}.issubset(fields):
        for row in reader:
            word = (row.get("word") or "").strip()
            sentence = (row.get("sentence") or "").strip()
            if not word or not sentence:
                continue

            normalized = crud.normalize_word(word)
            if normalized in seen_words:
                skipped_items += 1
                skipped_words.append(word)
                continue
            seen_words.add(normalized)

            if crud.get_entry_by_word(db, word):
                skipped_items += 1
                skipped_words.append(word)
                continue

            profile = crud.fetch_word_profile(word)
            try:
                crud.create_entry_with_profile(
                    db,
                    schemas.StudyEntryCreate(word=word, sentence=sentence),
                    profile,
                )
            except ValueError as exc:
                raise HTTPException(status_code=502, detail=f"{word}: {exc}") from exc
            imported_items += 1
    else:
        raise HTTPException(
            status_code=400,
            detail="CSV headers must be word,sentence",
        )

    return {
        "ok": True,
        "imported_items": imported_items,
        "skipped_items": skipped_items,
        "skipped_words": skipped_words,
    }
