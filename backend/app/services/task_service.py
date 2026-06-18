from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas
from .workflow_service import WorkflowService


class TaskService:
    """任务服务 - 任务的增删改查及列表查询"""

    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[models.AnnotationTask]:
        return db.query(models.AnnotationTask).filter(models.AnnotationTask.id == task_id).first()

    @staticmethod
    def get_task_or_404(db: Session, task_id: int) -> models.AnnotationTask:
        task = TaskService.get_task(db, task_id)
        if not task:
            raise ValueError("任务不存在")
        return task

    @staticmethod
    def create_task(db: Session, task_in: schemas.AnnotationTaskCreate) -> models.AnnotationTask:
        existing = (
            db.query(models.AnnotationTask)
            .filter(models.AnnotationTask.content_id == task_in.content_id)
            .first()
        )
        if existing:
            raise ValueError("content_id 已存在")
        task = models.AnnotationTask(**task_in.model_dump())
        db.add(task)
        db.flush()
        return task

    @staticmethod
    def list_tasks(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: Optional[schemas.TaskStatus] = None,
        consistency: Optional[schemas.ConsistencyStatus] = None,
        inspection: Optional[schemas.InspectionResult] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[schemas.TaskListItem], int]:
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

        items = [TaskService._to_task_list_item(db, t) for t in tasks]
        return items, total

    @staticmethod
    def _to_task_list_item(
        db: Session, task: models.AnnotationTask
    ) -> schemas.TaskListItem:
        ann = task.annotations
        insp = WorkflowService.get_latest_non_pending_inspection(db, task.id)
        return schemas.TaskListItem(
            id=task.id,
            content_id=task.content_id,
            title=task.title,
            content_type=task.content_type,
            status=task.status,
            consistency_status=ann.consistency_status if ann else None,
            consistency_score=ann.consistency_score if ann else None,
            annotator_a_name=ann.annotator_a.name if ann and ann.annotator_a else None,
            annotator_b_name=ann.annotator_b.name if ann and ann.annotator_b else None,
            inspection_result=insp.result if insp else None,
            updated_at=task.updated_at,
        )

    @staticmethod
    def get_task_inspections(db: Session, task_id: int) -> List[models.Inspection]:
        return (
            db.query(models.Inspection)
            .filter(models.Inspection.task_id == task_id)
            .order_by(models.Inspection.created_at.desc())
            .all()
        )
