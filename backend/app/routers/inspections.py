from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services import InspectionService

router = APIRouter(prefix="/api/inspections", tags=["质检管理"])


class ClaimRequest(BaseModel):
    inspector_id: int = 1
    inspector_name: str = "质检员-孙丽"


class ReleaseRequest(BaseModel):
    inspector_id: int = 1


class QuickPassRequest(BaseModel):
    task_ids: List[int]
    inspector_id: int = 1
    inspector_name: str = "质检员-孙丽"
    comment: str = "批量质检通过"


@router.post("/{task_id}", response_model=schemas.InspectionOut)
def create_or_update_inspection(
    task_id: int,
    inspection_in: schemas.InspectionSubmit,
    inspector_id: int = 1,
    inspector_name: str = "质检员-孙丽",
    db: Session = Depends(get_db),
):
    inspection, error = InspectionService.submit_inspection(
        db, task_id, inspection_in, inspector_id, inspector_name
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not inspection:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.commit()
    db.refresh(inspection)
    return inspection


@router.post("/{task_id}/claim")
def claim_task(
    task_id: int,
    req: ClaimRequest,
    db: Session = Depends(get_db),
):
    success, error, data = InspectionService.claim_task(
        db, task_id, req.inspector_id, req.inspector_name
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not success and not data:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.commit()
    return {"success": True, **data}


@router.post("/{task_id}/release")
def release_task(
    task_id: int,
    req: ReleaseRequest,
    db: Session = Depends(get_db),
):
    success, error = InspectionService.release_task(db, task_id, req.inspector_id)
    if error:
        if "不存在" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    db.commit()
    return {"success": True, "released": success}


@router.post("/batch/submit", response_model=schemas.BatchInspectionResult)
def batch_submit_inspections(
    req: schemas.BatchInspectionRequest,
    db: Session = Depends(get_db),
):
    result = InspectionService.batch_submit(
        db, req.items, req.inspector_id, req.inspector_name
    )
    db.commit()
    return result


@router.post("/batch/quick-pass", response_model=schemas.BatchInspectionResult)
def batch_quick_pass(
    req: QuickPassRequest,
    db: Session = Depends(get_db),
):
    result = InspectionService.batch_quick_pass(
        db, req.task_ids, req.inspector_id, req.inspector_name, req.comment
    )
    db.commit()
    return result


@router.get("/pending", response_model=List[schemas.TaskListItem])
def get_pending_inspections(
    inspector_id: int = 1,
    db: Session = Depends(get_db),
):
    return InspectionService.get_pending_inspections(db, inspector_id)
