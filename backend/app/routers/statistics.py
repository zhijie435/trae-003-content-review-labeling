from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services import StatisticsService

router = APIRouter(prefix="/api/statistics", tags=["数据统计"])


@router.get("", response_model=schemas.StatisticsOut)
def get_statistics(db: Session = Depends(get_db)):
    return StatisticsService.get_overall_statistics(db)


@router.get("/annotators")
def list_annotators(db: Session = Depends(get_db)):
    annotators = StatisticsService.list_annotators(db)
    return [a.model_dump() for a in annotators]
