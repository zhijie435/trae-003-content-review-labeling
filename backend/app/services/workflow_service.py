from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from .. import models

CLAIM_TIMEOUT_MINUTES = 30


class WorkflowService:
    """审核流状态机服务 - 统一管理任务状态流转和领取逻辑"""

    @staticmethod
    def is_claim_expired(claimed_at: Optional[datetime]) -> bool:
        if not claimed_at:
            return True
        return datetime.utcnow() - claimed_at > timedelta(minutes=CLAIM_TIMEOUT_MINUTES)

    @staticmethod
    def can_claim(task: models.AnnotationTask, target_status: models.TaskStatus) -> bool:
        if task.status != target_status:
            return False
        if task.claimed_by is None:
            return True
        if WorkflowService.is_claim_expired(task.claimed_at):
            return True
        return False

    @staticmethod
    def try_claim(
        task: models.AnnotationTask,
        user_id: int,
        user_name: str,
        target_status: models.TaskStatus,
    ) -> Tuple[bool, Optional[str]]:
        if task.status != target_status:
            return False, f"任务状态为 {task.status.value}，不允许领取"

        if task.claimed_by is None or WorkflowService.is_claim_expired(task.claimed_at):
            task.claimed_by = user_id
            task.claimed_by_name = user_name
            task.claimed_at = datetime.utcnow()
            return True, None

        if task.claimed_by == user_id:
            return True, None

        return False, f"任务已被 {task.claimed_by_name} 领取"

    @staticmethod
    def release(task: models.AnnotationTask, user_id: int) -> bool:
        if task.claimed_by == user_id:
            task.claimed_by = None
            task.claimed_by_name = None
            task.claimed_at = None
            return True
        return False

    @staticmethod
    def force_release(task: models.AnnotationTask) -> None:
        task.claimed_by = None
        task.claimed_by_name = None
        task.claimed_at = None

    @staticmethod
    def transition_to(task: models.AnnotationTask, target_status: models.TaskStatus) -> bool:
        task.status = target_status
        task.updated_at = datetime.utcnow()
        return True

    @staticmethod
    def start_double_annotation(task: models.AnnotationTask) -> bool:
        if task.status != models.TaskStatus.PENDING:
            return False
        task.status = models.TaskStatus.DOUBLE_ANNOTATING
        task.updated_at = datetime.utcnow()
        return True

    @staticmethod
    def complete_double_annotation(task: models.AnnotationTask) -> bool:
        if task.status != models.TaskStatus.DOUBLE_ANNOTATING:
            return False
        task.status = models.TaskStatus.WAITING_INSPECTION
        task.updated_at = datetime.utcnow()
        return True

    @staticmethod
    def start_inspection(task: models.AnnotationTask) -> bool:
        if task.status != models.TaskStatus.WAITING_INSPECTION:
            return False
        task.status = models.TaskStatus.INSPECTING
        task.updated_at = datetime.utcnow()
        return True

    @staticmethod
    def fail_inspection(task: models.AnnotationTask) -> bool:
        if task.status != models.TaskStatus.INSPECTING:
            return False
        task.status = models.TaskStatus.DOUBLE_ANNOTATING
        task.updated_at = datetime.utcnow()
        WorkflowService.force_release(task)
        return True

    @staticmethod
    def pass_inspection(task: models.AnnotationTask) -> bool:
        if task.status not in [
            models.TaskStatus.INSPECTING,
            models.TaskStatus.WAITING_INSPECTION,
        ]:
            return False
        task.status = models.TaskStatus.COMPLETED
        task.updated_at = datetime.utcnow()
        WorkflowService.force_release(task)
        return True

    @staticmethod
    def arbitrate_inspection(task: models.AnnotationTask) -> bool:
        if task.status not in [
            models.TaskStatus.INSPECTING,
            models.TaskStatus.WAITING_INSPECTION,
        ]:
            return False
        task.status = models.TaskStatus.COMPLETED
        task.updated_at = datetime.utcnow()
        WorkflowService.force_release(task)
        return True

    @staticmethod
    def get_latest_non_pending_inspection(
        db: Session, task_id: int
    ) -> Optional[models.Inspection]:
        return (
            db.query(models.Inspection)
            .filter(
                models.Inspection.task_id == task_id,
                models.Inspection.result != models.InspectionResult.PENDING,
            )
            .order_by(models.Inspection.created_at.desc())
            .first()
        )
