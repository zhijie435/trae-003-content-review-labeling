from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/inspections", tags=["质检管理"])


def _create_or_update_inspection(
    db: Session,
    task_id: int,
    inspection_in: schemas.InspectionSubmit,
    inspector_id: int,
    inspector_name: str,
):
    task = db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()
    if not task:
        return None

    existing = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.task_id == task_id,
            models.Inspection.inspector_id == inspector_id,
            models.Inspection.result == models.InspectionResult.PENDING,
        )
        .first()
    )

    if existing:
        existing.result = inspection_in.result
        existing.final_annotation = inspection_in.final_annotation
        existing.comment = inspection_in.comment
        existing.score = inspection_in.score
        existing.updated_at = datetime.utcnow()
        inspection = existing
    else:
        inspection = models.Inspection(
            task_id=task_id,
            inspector_id=inspector_id,
            inspector_name=inspector_name,
            result=inspection_in.result,
            final_annotation=inspection_in.final_annotation,
            comment=inspection_in.comment,
            score=inspection_in.score,
        )
        db.add(inspection)

    if inspection_in.result != models.InspectionResult.PENDING:
        task.status = models.TaskStatus.COMPLETED
    else:
        task.status = models.TaskStatus.INSPECTING

    return inspection


@router.post("/{task_id}", response_model=schemas.InspectionOut)
def create_or_update_inspection(
    task_id: int,
    inspection_in: schemas.InspectionSubmit,
    inspector_id: int = 1,
    inspector_name: str = "质检员-孙丽",
    db: Session = Depends(get_db),
):
    inspection = _create_or_update_inspection(db, task_id, inspection_in, inspector_id, inspector_name)
    if not inspection:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.commit()
    db.refresh(inspection)
    return inspection


@router.post("/batch/submit", response_model=schemas.BatchInspectionResult)
def batch_submit_inspections(
    req: schemas.BatchInspectionRequest,
    db: Session = Depends(get_db),
):
    success_count = 0
    failed_tasks: List[int] = []

    for item in req.items:
        inspection_in = schemas.InspectionSubmit(
            result=item.result,
            final_annotation=item.final_annotation,
            comment=item.comment,
            score=item.score,
        )
        inspection = _create_or_update_inspection(
            db, item.task_id, inspection_in, req.inspector_id, req.inspector_name
        )
        if inspection:
            success_count += 1
        else:
            failed_tasks.append(item.task_id)

    db.commit()

    return schemas.BatchInspectionResult(
        success_count=success_count,
        failed_count=len(failed_tasks),
        failed_tasks=failed_tasks,
    )


class QuickPassRequest(BaseModel):
    task_ids: List[int]
    inspector_id: int = 1
    inspector_name: str = "质检员-孙丽"
    comment: str = "批量质检通过"


@router.post("/batch/quick-pass", response_model=schemas.BatchInspectionResult)
def batch_quick_pass(
    req: QuickPassRequest,
    db: Session = Depends(get_db),
):
    success_count = 0
    failed_tasks: List[int] = []

    inspection_in = schemas.InspectionSubmit(
        result=models.InspectionResult.PASS,
        comment=req.comment,
    )

    for task_id in req.task_ids:
        inspection = _create_or_update_inspection(
            db, task_id, inspection_in, req.inspector_id, req.inspector_name
        )
        if inspection:
            success_count += 1
        else:
            failed_tasks.append(task_id)

    db.commit()

    return schemas.BatchInspectionResult(
        success_count=success_count,
        failed_count=len(failed_tasks),
        failed_tasks=failed_tasks,
    )


@router.get("/pending", response_model=List[schemas.TaskListItem])
def get_pending_inspections(db: Session = Depends(get_db)):
    tasks = (
        db.query(models.AnnotationTask)
        .filter(models.AnnotationTask.status == models.TaskStatus.WAITING_INSPECTION)
        .order_by(models.AnnotationTask.updated_at.desc())
        .limit(50)
        .all()
    )
    items = []
    for t in tasks:
        ann = t.annotations
        items.append(
            schemas.TaskListItem(
                id=t.id,
                content_id=t.content_id,
                title=t.title,
                content_type=t.content_type,
                status=t.status,
                consistency_status=ann.consistency_status if ann else None,
                consistency_score=ann.consistency_score if ann else None,
                annotator_a_name=ann.annotator_a.name if ann and ann.annotator_a else None,
                annotator_b_name=ann.annotator_b.name if ann and ann.annotator_b else None,
                inspection_result=None,
                updated_at=t.updated_at,
            )
        )
    return items
