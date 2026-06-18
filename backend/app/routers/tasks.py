from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from ..database import get_db
from ..models import Task, Annotation, User, UserRole, TaskStatus, AnnotationResult
from ..schemas import (
    TaskCreate,
    TaskResponse,
    TaskListResponse,
    AssignTaskRequest,
    DoubleAnnotationStats,
)
from ..auth import get_current_active_user, require_role

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])


@router.get("/", response_model=TaskListResponse)
def get_tasks(
    status: Optional[TaskStatus] = None,
    batch_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if batch_id:
        query = query.filter(Task.batch_id == batch_id)

    total = query.count()
    tasks = (
        query.order_by(Task.priority.desc(), Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TaskListResponse(
        total=total,
        items=tasks,
        page=page,
        page_size=page_size,
    )


@router.get("/stats/double-annotation", response_model=DoubleAnnotationStats)
def get_double_annotation_stats(
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Task)
    if batch_id:
        query = query.filter(Task.batch_id == batch_id)

    total_tasks = query.count()

    annotated_tasks = query.filter(Task.status == TaskStatus.ANNOTATED).all()
    consistent_count = 0
    inconsistent_count = 0

    for task in annotated_tasks:
        if len(task.annotations) >= 2:
            results = [ann.result for ann in task.annotations]
            if len(set(results)) == 1:
                consistent_count += 1
            else:
                inconsistent_count += 1

    in_quality_check = query.filter(Task.status == TaskStatus.IN_QUALITY_CHECK).count()
    quality_checked = query.filter(Task.status == TaskStatus.QUALITY_CHECKED).count()

    consistency_rate = (
        consistent_count / (consistent_count + inconsistent_count)
        if (consistent_count + inconsistent_count) > 0
        else 0.0
    )

    return DoubleAnnotationStats(
        total_tasks=total_tasks,
        consistent_tasks=consistent_count,
        inconsistent_tasks=inconsistent_count,
        consistency_rate=round(consistency_rate, 4),
        in_quality_check=in_quality_check,
        quality_checked=quality_checked,
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.post("/batch", response_model=List[TaskResponse])
def create_tasks_batch(
    tasks: List[TaskCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    db_tasks = [Task(**task.model_dump()) for task in tasks]
    db.add_all(db_tasks)
    db.commit()
    for task in db_tasks:
        db.refresh(task)
    return db_tasks


@router.post("/{task_id}/assign-double", response_model=TaskResponse)
def assign_double_annotation(
    task_id: int,
    request: AssignTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if len(request.annotator_ids) != 2:
        raise HTTPException(
            status_code=400,
            detail="Double annotation requires exactly 2 annotators",
        )

    for i, annotator_id in enumerate(request.annotator_ids):
        annotator = (
            db.query(User)
            .filter(User.id == annotator_id, User.role == UserRole.ANNOTATOR)
            .first()
        )
        if not annotator:
            raise HTTPException(
                status_code=404,
                detail=f"Annotator with id {annotator_id} not found",
            )

        existing = (
            db.query(Annotation)
            .filter(
                Annotation.task_id == task_id,
                Annotation.annotator_id == annotator_id,
            )
            .first()
        )
        if not existing:
            annotation = Annotation(
                task_id=task_id,
                annotator_id=annotator_id,
                result=AnnotationResult.PASS,
                annotation_index=i + 1,
            )
            db.add(annotation)

    task.status = TaskStatus.ASSIGNED
    db.commit()
    db.refresh(task)
    return task


@router.post("/batch/assign-double", response_model=dict)
def batch_assign_double_annotation(
    request: AssignTaskRequest,
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    if len(request.annotator_ids) != 2:
        raise HTTPException(
            status_code=400,
            detail="Double annotation requires exactly 2 annotators",
        )

    for annotator_id in request.annotator_ids:
        annotator = (
            db.query(User)
            .filter(User.id == annotator_id, User.role == UserRole.ANNOTATOR)
            .first()
        )
        if not annotator:
            raise HTTPException(
                status_code=404,
                detail=f"Annotator with id {annotator_id} not found",
            )

    query = db.query(Task).filter(Task.status == TaskStatus.PENDING)
    if batch_id:
        query = query.filter(Task.batch_id == batch_id)

    tasks = query.all()
    assigned_count = 0

    for task in tasks:
        for i, annotator_id in enumerate(request.annotator_ids):
            existing = (
                db.query(Annotation)
                .filter(
                    Annotation.task_id == task.id,
                    Annotation.annotator_id == annotator_id,
                )
                .first()
            )
            if not existing:
                annotation = Annotation(
                    task_id=task.id,
                    annotator_id=annotator_id,
                    result=AnnotationResult.PASS,
                    annotation_index=i + 1,
                )
                db.add(annotation)
        task.status = TaskStatus.ASSIGNED
        assigned_count += 1

    db.commit()
    return {"assigned_count": assigned_count}


@router.get("/my/assigned", response_model=List[TaskResponse])
def get_my_assigned_tasks(
    status: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = (
        db.query(Task)
        .join(Annotation)
        .filter(Annotation.annotator_id == current_user.id)
    )
    if status:
        query = query.filter(Task.status == status)
    else:
        query = query.filter(
            Task.status.in_([TaskStatus.ASSIGNED, TaskStatus.ANNOTATING])
        )

    tasks = query.order_by(Task.priority.desc(), Task.created_at.asc()).all()
    return tasks


@router.get("/random/next", response_model=TaskResponse)
def get_next_random_task(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.ANNOTATOR:
        tasks = (
            db.query(Task)
            .join(Annotation)
            .filter(
                Annotation.annotator_id == current_user.id,
                Task.status.in_([TaskStatus.ASSIGNED, TaskStatus.ANNOTATING]),
            )
            .all()
        )
    else:
        tasks = db.query(Task).filter(Task.status == TaskStatus.ANNOTATED).all()

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks available")

    return random.choice(tasks)
