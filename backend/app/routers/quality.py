from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from ..database import get_db
from ..models import (
    QualityCheck,
    Task,
    User,
    UserRole,
    TaskStatus,
    AnnotationResult,
    QualityStatus,
    Annotation,
    SampleBatch,
    SampleBatchTask,
)
from ..schemas import (
    QualityCheckCreate,
    QualityCheckUpdate,
    QualityCheckResponse,
    SampleBatchCreate,
    SampleBatchResponse,
)
from ..auth import get_current_active_user, require_role

router = APIRouter(prefix="/api/quality", tags=["质检抽样"])


@router.get("/checks", response_model=List[QualityCheckResponse])
def get_quality_checks(
    status: Optional[QualityStatus] = None,
    is_sampled: Optional[bool] = None,
    sample_batch_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(QualityCheck)

    if status:
        query = query.filter(QualityCheck.status == status)
    if is_sampled is not None:
        query = query.filter(QualityCheck.is_sampled == is_sampled)
    if sample_batch_id:
        query = query.filter(QualityCheck.sample_batch_id == sample_batch_id)

    checks = query.offset(skip).limit(limit).all()
    return checks


@router.get("/checks/{check_id}", response_model=QualityCheckResponse)
def get_quality_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    check = db.query(QualityCheck).filter(QualityCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")
    return check


@router.get("/my/tasks", response_model=List[Task])
def get_my_quality_tasks(
    status: Optional[QualityStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.QUALITY_CHECKER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not a quality checker")

    query = (
        db.query(Task)
        .join(QualityCheck)
        .filter(QualityCheck.checker_id == current_user.id)
    )
    if status:
        query = query.filter(QualityCheck.status == status)
    else:
        query = query.filter(QualityCheck.status == QualityStatus.PENDING)

    return query.all()


@router.post("/checks/{check_id}/submit", response_model=QualityCheckResponse)
def submit_quality_check(
    check_id: int,
    data: QualityCheckUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    check = db.query(QualityCheck).filter(QualityCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    if check.status != QualityStatus.PENDING:
        raise HTTPException(status_code=400, detail="Quality check already submitted")

    if data.final_result:
        check.final_result = data.final_result
    if data.remark:
        check.remark = data.remark

    if data.status:
        check.status = data.status
    elif data.final_result:
        check.status = QualityStatus.PASSED if data.final_result == AnnotationResult.PASS else QualityStatus.FAILED

    check.checker_id = current_user.id

    task = db.query(Task).filter(Task.id == check.task_id).first()
    if task:
        if check.status == QualityStatus.PASSED:
            task.status = TaskStatus.QUALITY_CHECKED
        elif check.status == QualityStatus.FAILED:
            task.status = TaskStatus.QUALITY_CHECKED
        elif check.status == QualityStatus.DISPUTED:
            task.status = TaskStatus.DISPUTED

    db.commit()
    db.refresh(check)
    return check


@router.post("/tasks/{task_id}/quality-check", response_model=QualityCheckResponse)
def create_quality_check(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.QUALITY_CHECKER)),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing = db.query(QualityCheck).filter(QualityCheck.task_id == task_id).first()
    if existing:
        return existing

    qc = QualityCheck(
        task_id=task_id,
        checker_id=current_user.id,
        status=QualityStatus.PENDING,
    )
    db.add(qc)

    if task.status != TaskStatus.IN_QUALITY_CHECK:
        task.status = TaskStatus.IN_QUALITY_CHECK

    db.commit()
    db.refresh(qc)
    return qc


@router.get("/sample-batches", response_model=List[SampleBatchResponse])
def get_sample_batches(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(SampleBatch)
    if status:
        query = query.filter(SampleBatch.status == status)
    return query.order_by(SampleBatch.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/sample-batches", response_model=SampleBatchResponse)
def create_sample_batch(
    batch: SampleBatchCreate,
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    task_query = db.query(Task).filter(Task.status == TaskStatus.ANNOTATED)
    if batch_id:
        task_query = task_query.filter(Task.batch_id == batch_id)

    all_tasks = task_query.all()
    total_count = len(all_tasks)

    sample_size = max(1, int(total_count * batch.sample_ratio))
    sampled_tasks = random.sample(all_tasks, min(sample_size, total_count)) if all_tasks else []

    sample_batch = SampleBatch(
        name=batch.name,
        batch_type=batch.batch_type,
        sample_ratio=batch.sample_ratio,
        sample_count=len(sampled_tasks),
        total_count=total_count,
        created_by=current_user.id,
    )
    db.add(sample_batch)
    db.flush()

    for task in sampled_tasks:
        sbt = SampleBatchTask(
            sample_batch_id=sample_batch.id,
            task_id=task.id,
        )
        db.add(sbt)

        existing_qc = db.query(QualityCheck).filter(QualityCheck.task_id == task.id).first()
        if not existing_qc:
            qc = QualityCheck(
                task_id=task.id,
                status=QualityStatus.PENDING,
                is_sampled=True,
                sample_batch_id=sample_batch.id,
            )
            db.add(qc)
            task.status = TaskStatus.IN_QUALITY_CHECK
        else:
            existing_qc.is_sampled = True
            existing_qc.sample_batch_id = sample_batch.id

    db.commit()
    db.refresh(sample_batch)
    return sample_batch


@router.get("/sample-batches/{batch_id}/tasks", response_model=List[Task])
def get_sample_batch_tasks(
    batch_id: int,
    is_checked: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    batch = db.query(SampleBatch).filter(SampleBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Sample batch not found")

    query = (
        db.query(Task)
        .join(SampleBatchTask)
        .filter(SampleBatchTask.sample_batch_id == batch_id)
    )

    if is_checked is not None:
        query = query.filter(SampleBatchTask.is_checked == is_checked)

    return query.all()


@router.get("/next-for-check", response_model=Task)
def get_next_task_for_check(
    sample_batch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.QUALITY_CHECKER)),
):
    query = db.query(QualityCheck).filter(QualityCheck.status == QualityStatus.PENDING)

    if sample_batch_id:
        query = query.filter(QualityCheck.sample_batch_id == sample_batch_id)

    checks = query.all()
    if not checks:
        raise HTTPException(status_code=404, detail="No tasks pending quality check")

    check = random.choice(checks)
    task = db.query(Task).filter(Task.id == check.task_id).first()
    return task


@router.get("/stats", response_model=dict)
def get_quality_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    total_qc = db.query(QualityCheck).count()
    pending = db.query(QualityCheck).filter(QualityCheck.status == QualityStatus.PENDING).count()
    passed = db.query(QualityCheck).filter(QualityCheck.status == QualityStatus.PASSED).count()
    failed = db.query(QualityCheck).filter(QualityCheck.status == QualityStatus.FAILED).count()
    disputed = db.query(QualityCheck).filter(QualityCheck.status == QualityStatus.DISPUTED).count()
    sampled = db.query(QualityCheck).filter(QualityCheck.is_sampled == True).count()

    pass_rate = (passed / total_qc) if total_qc > 0 else 0.0

    return {
        "total": total_qc,
        "pending": pending,
        "passed": passed,
        "failed": failed,
        "disputed": disputed,
        "sampled": sampled,
        "pass_rate": round(pass_rate, 4),
    }


@router.get("/annotations/compare/{task_id}", response_model=dict)
def compare_annotations(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    annotations = db.query(Annotation).filter(Annotation.task_id == task_id).all()

    if len(annotations) < 2:
        return {
            "task_id": task_id,
            "annotations_count": len(annotations),
            "is_consistent": None,
            "annotations": annotations,
        }

    results = [ann.result for ann in annotations]
    is_consistent = len(set(results)) == 1

    return {
        "task_id": task_id,
        "annotations_count": len(annotations),
        "is_consistent": is_consistent,
        "results": results,
        "annotations": annotations,
    }
