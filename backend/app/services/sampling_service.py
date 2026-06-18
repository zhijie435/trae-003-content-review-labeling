import random
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from .. import models, schemas
from .workflow_service import WorkflowService
from .task_service import TaskService


class SamplingService:
    """抽样服务 - 抽样批次管理、抽样策略"""

    @staticmethod
    def create_batch(
        db: Session,
        req: schemas.SamplingRequest,
    ) -> models.SamplingBatch:
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
            raise ValueError("没有符合条件的任务可抽样")

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
        db.flush()
        return batch

    @staticmethod
    def list_batches(
        db: Session,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[models.SamplingBatch], int]:
        query = db.query(models.SamplingBatch)
        total = query.count()
        batches = (
            query.order_by(models.SamplingBatch.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return batches, total

    @staticmethod
    def get_batch(db: Session, batch_id: int) -> Optional[models.SamplingBatch]:
        return (
            db.query(models.SamplingBatch)
            .filter(models.SamplingBatch.id == batch_id)
            .first()
        )

    @staticmethod
    def get_batch_or_404(db: Session, batch_id: int) -> models.SamplingBatch:
        batch = SamplingService.get_batch(db, batch_id)
        if not batch:
            raise ValueError("抽样批次不存在")
        return batch

    @staticmethod
    def get_batch_tasks(
        db: Session, batch_id: int
    ) -> List[schemas.TaskListItem]:
        batch = SamplingService.get_batch_or_404(db, batch_id)
        tasks = (
            db.query(models.AnnotationTask)
            .filter(models.AnnotationTask.id.in_(batch.task_ids))
            .all()
        )
        return [TaskService._to_task_list_item(db, t) for t in tasks]

    @staticmethod
    def get_batch_stats(db: Session, batch_id: int) -> schemas.SamplingBatchStats:
        batch = SamplingService.get_batch_or_404(db, batch_id)
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

            insp = WorkflowService.get_latest_non_pending_inspection(db, t.id)
            if insp:
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
