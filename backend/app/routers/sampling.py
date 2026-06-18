import random
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/sampling", tags=["抽样管理"])


@router.post("", response_model=schemas.SamplingBatchOut)
def create_sampling_batch(req: schemas.SamplingRequest, db: Session = Depends(get_db)):
    query = db.query(models.AnnotationTask).join(
        models.Annotation, models.Annotation.task_id == models.AnnotationTask.id
    )

    query = query.filter(
        models.AnnotationTask.status.in_(
            [models.TaskStatus.WAITING_INSPECTION, models.TaskStatus.COMPLETED]
        )
    )

    if req.consistency_filter:
        query = query.filter(models.Annotation.consistency_status == req.consistency_filter)

    available_tasks = query.all()

    if not available_tasks:
        raise HTTPException(status_code=400, detail="没有符合条件的任务可抽样")

    if req.sample_ratio is not None:
        sample_count = max(1, int(len(available_tasks) * req.sample_ratio))
    else:
        sample_count = req.sample_count

    sample_count = min(sample_count, len(available_tasks))

    if req.strategy == "inconsistent_first":
        available_tasks.sort(
            key=lambda t: (
                t.annotations.consistency_score if t.annotations else 1.0
            )
        )
        sampled = available_tasks[:sample_count]
    elif req.strategy == "high_score_first":
        available_tasks.sort(
            key=lambda t: -(
                t.annotations.consistency_score if t.annotations else 0.0
            )
        )
        sampled = available_tasks[:sample_count]
    else:
        sampled = random.sample(available_tasks, sample_count)

    task_ids = [t.id for t in sampled]

    batch = models.SamplingBatch(
        name=req.name,
        description=req.description,
        sample_count=sample_count,
        sample_ratio=req.sample_ratio,
        strategy=req.strategy,
        consistency_filter=req.consistency_filter.value if req.consistency_filter else None,
        task_ids=task_ids,
        created_by=req.created_by,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/batches", response_model=List[schemas.SamplingBatchOut])
def list_sampling_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    batches = (
        db.query(models.SamplingBatch)
        .order_by(models.SamplingBatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return batches


@router.get("/batches/{batch_id}", response_model=schemas.SamplingBatchOut)
def get_sampling_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.SamplingBatch).filter(models.SamplingBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="抽样批次不存在")
    return batch


@router.get("/batches/{batch_id}/tasks", response_model=List[schemas.TaskListItem])
def get_batch_tasks(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.SamplingBatch).filter(models.SamplingBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="抽样批次不存在")

    tasks = (
        db.query(models.AnnotationTask)
        .filter(models.AnnotationTask.id.in_(batch.task_ids))
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
    return items


@router.get("/batches/{batch_id}/stats", response_model=schemas.SamplingBatchStats)
def get_batch_stats(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.SamplingBatch).filter(models.SamplingBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="抽样批次不存在")

    tasks = (
        db.query(models.AnnotationTask)
        .filter(models.AnnotationTask.id.in_(batch.task_ids))
        .all()
    )

    total_tasks = len(tasks)
    inspected_count = 0
    pending_count = 0
    pass_count = 0
    fail_count = 0
    arbitrated_count = 0
    inconsistent_count = 0
    consistent_count = 0
    partial_count = 0

    for t in tasks:
        ann = t.annotations
        if ann:
            if ann.consistency_status == models.ConsistencyStatus.CONSISTENT:
                consistent_count += 1
            elif ann.consistency_status == models.ConsistencyStatus.INCONSISTENT:
                inconsistent_count += 1
            elif ann.consistency_status == models.ConsistencyStatus.PARTIAL:
                partial_count += 1

        insp = t.inspections[-1] if t.inspections else None
        if insp and insp.result != models.InspectionResult.PENDING:
            inspected_count += 1
            if insp.result == models.InspectionResult.PASS:
                pass_count += 1
            elif insp.result == models.InspectionResult.FAIL:
                fail_count += 1
            elif insp.result == models.InspectionResult.ARBITRATED:
                arbitrated_count += 1
        else:
            pending_count += 1

    pass_rate = (pass_count + arbitrated_count) / inspected_count if inspected_count > 0 else 0.0
    misjudgment_rate = fail_count / inspected_count if inspected_count > 0 else 0.0

    return schemas.SamplingBatchStats(
        batch_id=batch.id,
        batch_name=batch.name,
        total_tasks=total_tasks,
        inspected_count=inspected_count,
        pending_count=pending_count,
        pass_count=pass_count,
        fail_count=fail_count,
        arbitrated_count=arbitrated_count,
        pass_rate=round(pass_rate, 4),
        misjudgment_rate=round(misjudgment_rate, 4),
        inconsistent_count=inconsistent_count,
        consistent_count=consistent_count,
        partial_count=partial_count,
    )
