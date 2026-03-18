from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/review", tags=["review"])


@router.get("", response_model=schemas.ReviewUnifiedResponse)
def get_review(period: str = "weekly", limit: int = 30, db: Session = Depends(get_db)):
    items = crud.get_review_entries(db, period=period, limit=limit)
    return {
        "period": period,
        "items": [crud.serialize_entry(row) for row in items],
    }
