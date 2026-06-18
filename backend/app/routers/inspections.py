from typing import List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/inspections", tags=["质检管理"])

CLAIM_TIMEOUT_MINUTES = 30


class ClaimRequest(BaseModel):
    inspector_id: int = 1
    inspector_name: str = "质检员-孙丽"


class ReleaseRequest(BaseModel):
    inspector_id: int = 1


def _is_claim_expired(claimed_at: datetime) -> bool:
    if not claimed_at:
        return True
    return datetime.utcnow() - claimed_at > timedelta(minutes=CLAIM_TIMEOUT_MINUTES)


def _try_claim_task(
    db: Session,
    task: models.AnnotationTask,
    inspector_id: int,
    inspector_name: str,
) -> bool:
    if task.status != models.TaskStatus.WAITING_INSPECTION:
        return False

    if task.claimed_by is None or _is_claim_expired(task.claimed_at):
        task.claimed_by = inspector_id
        task.claimed_by_name = inspector_name
        task.claimed_at = datetime.utcnow()
        return True

    return task.claimed_by == inspector_id


def _release_task(db: Session, task: models.AnnotationTask, inspector_id: int) -> bool:
    if task.claimed_by == inspector_id:
        task.claimed_by = None
        task.claimed_by_name = None
        task.claimed_at = None
        return True
    return False


def _create_or_update_inspection(
    db: Session,
    task_id: int,
    inspection_in: schemas.InspectionSubmit,
    inspector_id: int,
    inspector_name: str,
):
    task = db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()
    if not task:
        return None, "任务不存在"

    if not _try_claim_task(db, task, inspector_id, inspector_name):
        if task.claimed_by and task.claimed_by != inspector_id:
            return None, f"任务已被 {task.claimed_by_name} 领取，请选择其他任务"
        return None, "任务状态不允许质检"

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

    if inspection_in.result == models.InspectionResult.PENDING:
        task.status = models.TaskStatus.INSPECTING
    elif inspection_in.result == models.InspectionResult.FAIL:
        task.status = models.TaskStatus.DOUBLE_ANNOTATING
        _release_task(db, task, inspector_id)
    else:
        task.status = models.TaskStatus.COMPLETED
        _release_task(db, task, inspector_id)

    return inspection, None


@router.post("/{task_id}", response_model=schemas.InspectionOut)
def create_or_update_inspection(
    task_id: int,
    inspection_in: schemas.InspectionSubmit,
    inspector_id: int = 1,
    inspector_name: str = "质检员-孙丽",
    db: Session = Depends(get_db),
):
    inspection, error = _create_or_update_inspection(db, task_id, inspection_in, inspector_id, inspector_name)
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
    task = db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if _try_claim_task(db, task, req.inspector_id, req.inspector_name):
        db.commit()
        return {
            "success": True,
            "claimed": True,
            "claimed_by": task.claimed_by,
            "claimed_by_name": task.claimed_by_name,
            "claimed_at": task.claimed_at,
        }
    else:
        return {
            "success": True,
            "claimed": False,
            "claimed_by": task.claimed_by,
            "claimed_by_name": task.claimed_by_name,
            "claimed_at": task.claimed_at,
            "message": f"任务已被 {task.claimed_by_name} 领取",
        }


@router.post("/{task_id}/release")
def release_task(
    task_id: int,
    req: ReleaseRequest,
    db: Session = Depends(get_db),
):
    task = db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if _release_task(db, task, req.inspector_id):
        db.commit()
        return {"success": True, "released": True}
    else:
        raise HTTPException(status_code=400, detail="无法释放，任务不是由您领取的")


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
        inspection, error = _create_or_update_inspection(
            db, item.task_id, inspection_in, req.inspector_id, req.inspector_name
        )
        if inspection and not error:
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
        inspection, error = _create_or_update_inspection(
            db, task_id, inspection_in, req.inspector_id, req.inspector_name
        )
        if inspection and not error:
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
def get_pending_inspections(
    inspector_id: int = 1,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    timeout_threshold = now - timedelta(minutes=CLAIM_TIMEOUT_MINUTES)

    tasks = (
        db.query(models.AnnotationTask)
        .filter(
            models.AnnotationTask.status == models.TaskStatus.WAITING_INSPECTION,
            (
                (models.AnnotationTask.claimed_by.is_(None))
                | (models.AnnotationTask.claimed_at < timeout_threshold)
                | (models.AnnotationTask.claimed_by == inspector_id)
            ),
        )
        .order_by(models.AnnotationTask.updated_at.desc())
        .limit(50)
        .all()
    )
    items = []
    for t in tasks:
        ann = t.annotations
        is_claimed_by_others = (
            t.claimed_by is not None
            and t.claimed_by != inspector_id
            and not _is_claim_expired(t.claimed_at)
        )
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
