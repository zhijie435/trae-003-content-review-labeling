from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import (
    Annotation,
    Task,
    User,
    UserRole,
    TaskStatus,
    AnnotationResult,
    QualityCheck,
    QualityStatus,
)
from ..schemas import AnnotationCreate, AnnotationResponse
from ..auth import get_current_active_user, require_role

router = APIRouter(prefix="/api/annotations", tags=["标注"])


@router.get("/", response_model=List[AnnotationResponse])
def get_annotations(
    task_id: int = None,
    annotator_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Annotation)
    if task_id:
        query = query.filter(Annotation.task_id == task_id)
    if annotator_id:
        query = query.filter(Annotation.annotator_id == annotator_id)
    return query.all()


@router.get("/{annotation_id}", response_model=AnnotationResponse)
def get_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return annotation


@router.post("/", response_model=AnnotationResponse)
def create_annotation(
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == annotation.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_annotation = (
        db.query(Annotation)
        .filter(
            Annotation.task_id == annotation.task_id,
            Annotation.annotator_id == current_user.id,
        )
        .first()
    )

    if existing_annotation:
        existing_annotation.result = annotation.result
        existing_annotation.remark = annotation.remark
        existing_annotation.tags = annotation.tags
        db.commit()
        db.refresh(existing_annotation)
        annotation_obj = existing_annotation
    else:
        db_annotation = Annotation(
            **annotation.model_dump(),
            annotator_id=current_user.id,
        )
        db.add(db_annotation)
        db.commit()
        db.refresh(db_annotation)
        annotation_obj = db_annotation

    _update_task_status_after_annotation(task.id, db)

    return annotation_obj


@router.put("/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: int,
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    if annotation.annotator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed to update this annotation")

    annotation.result = annotation_data.result
    annotation.remark = annotation_data.remark
    annotation.tags = annotation_data.tags

    db.commit()
    db.refresh(annotation)
    return annotation


@router.post("/submit/{task_id}", response_model=Task)
def submit_annotation(
    task_id: int,
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.ASSIGNED, TaskStatus.ANNOTATING]:
        raise HTTPException(status_code=400, detail="Task is not in annotatable state")

    existing = (
        db.query(Annotation)
        .filter(
            Annotation.task_id == task_id,
            Annotation.annotator_id == current_user.id,
        )
        .first()
    )

    if existing:
        existing.result = annotation.result
        existing.remark = annotation.remark
        existing.tags = annotation.tags
    else:
        new_annotation = Annotation(
            task_id=task_id,
            annotator_id=current_user.id,
            result=annotation.result,
            remark=annotation.remark,
            tags=annotation.tags,
        )
        db.add(new_annotation)

    _update_task_status_after_annotation(task_id, db)
    db.refresh(task)
    return task


def _update_task_status_after_annotation(task_id: int, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return

    annotations = db.query(Annotation).filter(Annotation.task_id == task_id).all()
    submitted_count = sum(1 for a in annotations if a.result is not None)

    if submitted_count >= 2:
        task.status = TaskStatus.ANNOTATED

        results = [a.result for a in annotations]
        if len(set(results)) > 1:
            task.status = TaskStatus.IN_QUALITY_CHECK
            _create_quality_check_for_inconsistent(task_id, db)
    elif submitted_count == 1:
        task.status = TaskStatus.ANNOTATING

    db.commit()


def _create_quality_check_for_inconsistent(task_id: int, db: Session):
    existing = db.query(QualityCheck).filter(QualityCheck.task_id == task_id).first()
    if not existing:
        qc = QualityCheck(
            task_id=task_id,
            status=QualityStatus.PENDING,
            is_sampled=False,
        )
        db.add(qc)
        db.commit()
