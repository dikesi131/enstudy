from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=schemas.StatsUnifiedOverview)
def get_stats_overview(db: Session = Depends(get_db)):
    return crud.get_unified_stats(db)
