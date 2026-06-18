from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/statistics", tags=["数据统计"])


def _get_latest_inspection_by_task(db: Session):
    subquery = (
        db.query(
            models.Inspection.task_id,
            func.max(models.Inspection.created_at).label("max_created"),
        )
        .filter(models.Inspection.result != models.InspectionResult.PENDING)
        .group_by(models.Inspection.task_id)
        .subquery()
    )

    latest_inspections = (
        db.query(models.Inspection)
        .join(
            subquery,
            (models.Inspection.task_id == subquery.c.task_id)
            & (models.Inspection.created_at == subquery.c.max_created),
        )
        .all()
    )
    return latest_inspections


@router.get("", response_model=schemas.StatisticsOut)
def get_statistics(db: Session = Depends(get_db)):
    total_tasks = db.query(func.count(models.AnnotationTask.id)).scalar() or 0

    double_annotated = (
        db.query(func.count(models.Annotation.id)).scalar() or 0
    )

    waiting_inspection = (
        db.query(func.count(models.AnnotationTask.id))
        .filter(models.AnnotationTask.status == models.TaskStatus.WAITING_INSPECTION)
        .scalar()
        or 0
    )

    inspected = (
        db.query(func.count(models.AnnotationTask.id))
        .filter(models.AnnotationTask.status == models.TaskStatus.COMPLETED)
        .scalar()
        or 0
    )

    consistent_count = (
        db.query(func.count(models.Annotation.id))
        .filter(models.Annotation.consistency_status == models.ConsistencyStatus.CONSISTENT)
        .scalar()
        or 0
    )
    inconsistent_count = (
        db.query(func.count(models.Annotation.id))
        .filter(models.Annotation.consistency_status == models.ConsistencyStatus.INCONSISTENT)
        .scalar()
        or 0
    )
    partial_count = (
        db.query(func.count(models.Annotation.id))
        .filter(models.Annotation.consistency_status == models.ConsistencyStatus.PARTIAL)
        .scalar()
        or 0
    )

    consistency_rate = (
        consistent_count / double_annotated if double_annotated > 0 else 0.0
    )

    latest_inspections = _get_latest_inspection_by_task(db)
    pass_count = 0
    fail_count = 0
    arbitrated_count = 0
    for insp in latest_inspections:
        if insp.result == models.InspectionResult.PASS:
            pass_count += 1
        elif insp.result == models.InspectionResult.FAIL:
            fail_count += 1
        elif insp.result == models.InspectionResult.ARBITRATED:
            arbitrated_count += 1

    total_inspections = pass_count + fail_count + arbitrated_count
    pass_rate = (
        (pass_count + arbitrated_count) / total_inspections
        if total_inspections > 0
        else 0.0
    )

    total_sampling_batches = (
        db.query(func.count(models.SamplingBatch.id)).scalar() or 0
    )

    annotators = db.query(models.Annotator).all()
    per_annotator_stats = []
    for a in annotators:
        tasks_as_a = (
            db.query(func.count(models.Annotation.id))
            .filter(models.Annotation.annotator_a_id == a.id)
            .scalar()
            or 0
        )
        tasks_as_b = (
            db.query(func.count(models.Annotation.id))
            .filter(models.Annotation.annotator_b_id == a.id)
            .scalar()
            or 0
        )
        total = tasks_as_a + tasks_as_b

        consistent_as_a = (
            db.query(func.count(models.Annotation.id))
            .filter(
                models.Annotation.annotator_a_id == a.id,
                models.Annotation.consistency_status == models.ConsistencyStatus.CONSISTENT,
            )
            .scalar()
            or 0
        )
        consistent_as_b = (
            db.query(func.count(models.Annotation.id))
            .filter(
                models.Annotation.annotator_b_id == a.id,
                models.Annotation.consistency_status == models.ConsistencyStatus.CONSISTENT,
            )
            .scalar()
            or 0
        )
        consistent_total = consistent_as_a + consistent_as_b
        consistency_rate_a = consistent_total / total if total > 0 else 0.0

        per_annotator_stats.append(
            {
                "annotator_id": a.id,
                "name": a.name,
                "total_tasks": total,
                "consistent_count": consistent_total,
                "consistency_rate": round(consistency_rate_a, 4),
            }
        )

    return schemas.StatisticsOut(
        total_tasks=total_tasks,
        double_annotated=double_annotated,
        waiting_inspection=waiting_inspection,
        inspected=inspected,
        consistent_count=consistent_count,
        inconsistent_count=inconsistent_count,
        partial_count=partial_count,
        consistency_rate=round(consistency_rate, 4),
        pass_count=pass_count,
        fail_count=fail_count,
        arbitrated_count=arbitrated_count,
        pass_rate=round(pass_rate, 4),
        total_sampling_batches=total_sampling_batches,
        per_annotator_stats=per_annotator_stats,
    )


@router.get("/annotators")
def list_annotators(db: Session = Depends(get_db)):
    annotators = db.query(models.Annotator).all()
    return [
        schemas.AnnotatorOut.model_validate(a).model_dump() for a in annotators
    ]
