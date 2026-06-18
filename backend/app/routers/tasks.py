import random
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/tasks", tags=["标注任务"])


@router.get("", response_model=schemas.TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[schemas.TaskStatus] = None,
    consistency: Optional[schemas.ConsistencyStatus] = None,
    inspection: Optional[schemas.InspectionResult] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.AnnotationTask).outerjoin(models.Annotation)

    if status:
        query = query.filter(models.AnnotationTask.status == status)
    if consistency:
        query = query.filter(models.Annotation.consistency_status == consistency)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                models.AnnotationTask.title.like(like),
                models.AnnotationTask.content.like(like),
                models.AnnotationTask.content_id.like(like),
            )
        )

    total = query.count()
    tasks = (
        query.order_by(models.AnnotationTask.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for t in tasks:
        ann = t.annotations
        insp = t.inspections[-1] if t.inspections else None
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
                inspection_result=insp.result if insp else None,
                updated_at=t.updated_at,
            )
        )

    return schemas.TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=schemas.AnnotationTaskDetail)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/{task_id}/inspections", response_model=List[schemas.InspectionOut])
def get_task_inspections(task_id: int, db: Session = Depends(get_db)):
    inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.task_id == task_id)
        .order_by(models.Inspection.created_at.desc())
        .all()
    )
    return inspections


@router.post("", response_model=schemas.AnnotationTaskOut)
def create_task(task_in: schemas.AnnotationTaskCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.AnnotationTask)
        .filter(models.AnnotationTask.content_id == task_in.content_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="content_id 已存在")
    task = models.AnnotationTask(**task_in.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
