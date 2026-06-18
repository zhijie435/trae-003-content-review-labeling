from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services import SamplingService

router = APIRouter(prefix="/api/sampling", tags=["抽样管理"])


@router.post("", response_model=schemas.SamplingBatchOut)
def create_sampling_batch(req: schemas.SamplingRequest, db: Session = Depends(get_db)):
    try:
        batch = SamplingService.create_batch(db, req)
        db.commit()
        db.refresh(batch)
        return batch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batches", response_model=List[schemas.SamplingBatchOut])
def list_sampling_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    batches, _ = SamplingService.list_batches(db, page=page, page_size=page_size)
    return batches


@router.get("/batches/{batch_id}", response_model=schemas.SamplingBatchOut)
def get_sampling_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = SamplingService.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="抽样批次不存在")
    return batch


@router.get("/batches/{batch_id}/tasks", response_model=List[schemas.TaskListItem])
def get_batch_tasks(batch_id: int, db: Session = Depends(get_db)):
    try:
        return SamplingService.get_batch_tasks(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/batches/{batch_id}/stats", response_model=schemas.SamplingBatchStats)
def get_batch_stats(batch_id: int, db: Session = Depends(get_db)):
    try:
        return SamplingService.get_batch_stats(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
