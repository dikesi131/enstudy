from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=schemas.ReviewUnifiedResponse)
def get_review(limit: int = 30, db: Session = Depends(get_db)):
    items = crud.get_review_entries(db, limit=limit)
    return {
        "period": "daily",
        "items": [crud.serialize_entry(row) for row in items],
    }


@router.post("/{entry_id}/complete", response_model=schemas.StudyEntryRead)
def complete_review(
    entry_id: int,
    payload: schemas.ReviewCompleteRequest,
    db: Session = Depends(get_db),
):
    row = crud.mark_entry_reviewed(db, entry_id, outcome=payload.outcome)
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return crud.serialize_entry(row)
