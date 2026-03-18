from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=list[schemas.StudyEntryRead])
def get_entries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    rows = crud.list_entries(db, skip=skip, limit=limit)
    return [crud.serialize_entry(row) for row in rows]


@router.post("", response_model=schemas.StudyEntryRead)
def add_entry(payload: schemas.StudyEntryCreate, db: Session = Depends(get_db)):
    existing = crud.get_entry_by_word(db, payload.word)
    if existing:
        raise HTTPException(status_code=409, detail=f"单词已存在，已跳过: {payload.word}")
    try:
        row = crud.create_entry(db, payload)
        return crud.serialize_entry(row)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{entry_id}")
def remove_entry(entry_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_entry(db, entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"ok": True}
