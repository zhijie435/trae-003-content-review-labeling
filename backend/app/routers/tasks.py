from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services import TaskService

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
    items, total = TaskService.list_tasks(
        db,
        page=page,
        page_size=page_size,
        status=status,
        consistency=consistency,
        inspection=inspection,
        keyword=keyword,
    )
    return schemas.TaskListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=schemas.AnnotationTaskDetail)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/{task_id}/inspections", response_model=list[schemas.InspectionOut])
def get_task_inspections(task_id: int, db: Session = Depends(get_db)):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskService.get_task_inspections(db, task_id)


@router.post("", response_model=schemas.AnnotationTaskOut)
def create_task(task_in: schemas.AnnotationTaskCreate, db: Session = Depends(get_db)):
    try:
        task = TaskService.create_task(db, task_in)
        db.commit()
        db.refresh(task)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
