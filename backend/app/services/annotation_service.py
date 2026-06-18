from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from .. import models, schemas
from .workflow_service import WorkflowService
from .task_service import TaskService


class AnnotationService:
    """标注服务 - 标注的领取、提交、一致性检查"""

    @staticmethod
    def claim_for_annotation(
        db: Session,
        task_id: int,
        annotator_id: int,
        annotator_name: str,
    ) -> Tuple[bool, Optional[str], Optional[models.AnnotationTask]]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return False, "任务不存在", None

        success, error = WorkflowService.try_claim(
            task, annotator_id, annotator_name, models.TaskStatus.DOUBLE_ANNOTATING
        )
        if not success:
            return False, error, None

        annotation = task.annotations
        if not annotation:
            return True, None, task

        is_annotator_a = annotation.annotator_a_id == annotator_id
        is_annotator_b = annotation.annotator_b_id == annotator_id

        if not is_annotator_a and not is_annotator_b:
            return False, "您不是该任务的标注员", None

        return True, None, task

    @staticmethod
    def submit_annotation(
        db: Session,
        task_id: int,
        annotator_id: int,
        annotation_result: dict,
    ) -> Tuple[Optional[models.Annotation], Optional[str]]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return None, "任务不存在"

        if task.status != models.TaskStatus.DOUBLE_ANNOTATING:
            return None, f"任务状态为 {task.status.value}，不允许提交标注"

        if task.claimed_by != annotator_id:
            return None, "请先领取该任务"

        annotation = task.annotations
        if not annotation:
            return None, "标注记录不存在"

        is_annotator_a = annotation.annotator_a_id == annotator_id
        is_annotator_b = annotation.annotator_b_id == annotator_id

        if not is_annotator_a and not is_annotator_b:
            return None, "您不是该任务的标注员"

        if is_annotator_a:
            annotation.result_a = annotation_result
            annotation.annotated_at_a = datetime.utcnow()
        else:
            annotation.result_b = annotation_result
            annotation.annotated_at_b = datetime.utcnow()

        if annotation.annotated_at_a and annotation.annotated_at_b:
            AnnotationService._check_consistency(annotation)
            WorkflowService.complete_double_annotation(task)

        WorkflowService.release(task, annotator_id)
        db.flush()

        return annotation, None

    @staticmethod
    def _check_consistency(annotation: models.Annotation) -> None:
        result_a = annotation.result_a or {}
        result_b = annotation.result_b or {}

        keys_a = set(result_a.keys())
        keys_b = set(result_b.keys())
        all_keys = keys_a | keys_b

        if not all_keys:
            annotation.consistency_status = models.ConsistencyStatus.UNCHECKED
            annotation.consistency_score = None
            annotation.diff_detail = None
            return

        same_count = 0
        diff_items = {}

        for key in all_keys:
            val_a = result_a.get(key)
            val_b = result_b.get(key)
            if val_a == val_b:
                same_count += 1
            else:
                diff_items[key] = {"a": val_a, "b": val_b}

        score = same_count / len(all_keys) if all_keys else 0.0
        annotation.consistency_score = round(score, 4)
        annotation.diff_detail = diff_items

        if score == 1.0:
            annotation.consistency_status = models.ConsistencyStatus.CONSISTENT
        elif score >= 0.6:
            annotation.consistency_status = models.ConsistencyStatus.PARTIAL
        else:
            annotation.consistency_status = models.ConsistencyStatus.INCONSISTENT

    @staticmethod
    def create_annotation(
        db: Session,
        task_id: int,
        annotator_a_id: int,
        annotator_b_id: int,
    ) -> models.Annotation:
        existing = (
            db.query(models.Annotation)
            .filter(models.Annotation.task_id == task_id)
            .first()
        )
        if existing:
            raise ValueError("该任务已有标注记录")

        annotation = models.Annotation(
            task_id=task_id,
            annotator_a_id=annotator_a_id,
            annotator_b_id=annotator_b_id,
            result_a={},
            result_b={},
        )
        db.add(annotation)
        db.flush()
        return annotation

    @staticmethod
    def get_pending_annotation_tasks(
        db: Session,
        annotator_id: int,
        limit: int = 50,
    ) -> List[schemas.TaskListItem]:
        tasks = (
            db.query(models.AnnotationTask)
            .join(
                models.Annotation,
                models.Annotation.task_id == models.AnnotationTask.id,
            )
            .filter(
                models.AnnotationTask.status == models.TaskStatus.DOUBLE_ANNOTATING,
                (
                    (models.Annotation.annotator_a_id == annotator_id)
                    | (models.Annotation.annotator_b_id == annotator_id)
                ),
            )
            .order_by(models.AnnotationTask.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [TaskService._to_task_list_item(db, t) for t in tasks]
