from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from .. import models

CLAIM_TIMEOUT_MINUTES = 30


class WorkflowService:
    """审核流状态机服务 - 统一管理任务状态流转和领取逻辑

    并发安全策略：
    - try_claim 使用 DB 层面 原子 UPDATE ... WHERE（CAS 模式），
      而不是 ORM 对象的内存式 check-then-act。
    """

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
        db: Session,
        task: models.AnnotationTask,
        user_id: int,
        user_name: str,
        target_status: models.TaskStatus,
    ) -> Tuple[bool, Optional[str]]:
        """原子领取 —— 通过 DB 层 UPDATE ... WHERE 避免 check-then-act 竞态。

        **并发安全保证**：
        UPDATE ... WHERE (claimed_by IS NULL OR expired OR claimed_by=me)
        通过数据库行锁 + WHERE 条件原子判断，rowcount 精确指示是否抢到。
        使用 synchronize_session=False 完全禁用 SQLAlchemy 的同步魔法，
        自己控制 ORM 对象状态，避免任何意外副作用。
        """
        task_id = task.id
        now = datetime.utcnow()
        timeout_cutoff = now - timedelta(minutes=CLAIM_TIMEOUT_MINUTES)

        # ---- 快速路径：如果该 session 里 task 已经是当前用户且未过期 ----
        # （在同一个 session 的连续调用场景下，省一次 UPDATE）
        if task.claimed_by == user_id and task.status == target_status:
            if not WorkflowService.is_claim_expired(task.claimed_at):
                return True, None

        # ---- 原子 CAS 更新 ----
        from sqlalchemy import update

        stmt = (
            update(models.AnnotationTask)
            .where(
                models.AnnotationTask.id == task_id,
                models.AnnotationTask.status == target_status,
                or_(
                    models.AnnotationTask.claimed_by.is_(None),
                    models.AnnotationTask.claimed_at < timeout_cutoff,
                    models.AnnotationTask.claimed_by == user_id,
                ),
            )
            .values(
                claimed_by=user_id,
                claimed_by_name=user_name,
                claimed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        result = db.execute(stmt)
        db.flush()

        affected = result.rowcount  # type: ignore[attr-defined]

        if affected >= 1:
            # ---- 抢到：同步 ORM 对象属性到最新 DB 状态 ----
            db.expire(task, ["claimed_by", "claimed_by_name", "claimed_at", "updated_at"])
            db.refresh(task)
            return True, None

        # ---- 没抢到：刷新对象，从最新 DB 状态生成准确错误 ----
        db.refresh(task)
        if task.status != target_status:
            return False, f"任务状态为 {task.status.value}，不允许领取"
        if task.claimed_by == user_id:
            # 极小概率兜底：refresh 发现其实就是自己（续期竞态恰好闭环）
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
