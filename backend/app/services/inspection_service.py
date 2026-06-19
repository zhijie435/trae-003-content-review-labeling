from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from .workflow_service import WorkflowService, CLAIM_TIMEOUT_MINUTES
from .task_service import TaskService


class InspectionService:
    """质检服务 - 质检的领取、提交、批量操作

    并发安全策略：
    - try_claim: DB 原子 UPDATE ... WHERE（见 workflow_service）
    - PENDING inspection 去重: (task_id, inspector_id)  WHERE result='pending' 唯一索引
      + 捕获 IntegrityError 后重试查询 + 更新
    """

    @staticmethod
    def claim_task(
        db: Session,
        task_id: int,
        inspector_id: int,
        inspector_name: str,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return False, "任务不存在", None

        success, error = WorkflowService.try_claim(
            db, task, inspector_id, inspector_name, models.TaskStatus.WAITING_INSPECTION
        )
        if not success:
            if task.claimed_by and task.claimed_by != inspector_id:
                return True, None, {
                    "claimed": False,
                    "claimed_by": task.claimed_by,
                    "claimed_by_name": task.claimed_by_name,
                    "claimed_at": task.claimed_at,
                    "message": f"任务已被 {task.claimed_by_name} 领取",
                }
            return False, error, None

        return True, None, {
            "claimed": True,
            "claimed_by": task.claimed_by,
            "claimed_by_name": task.claimed_by_name,
            "claimed_at": task.claimed_at,
        }

    @staticmethod
    def release_task(
        db: Session,
        task_id: int,
        inspector_id: int,
    ) -> Tuple[bool, Optional[str]]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return False, "任务不存在"

        if WorkflowService.release(task, inspector_id):
            return True, None
        return False, "无法释放，任务不是由您领取的"

    @staticmethod
    def submit_inspection(
        db: Session,
        task_id: int,
        inspection_in: schemas.InspectionSubmit,
        inspector_id: int,
        inspector_name: str,
    ) -> Tuple[Optional[models.Inspection], Optional[str]]:
        task = TaskService.get_task(db, task_id)
        if not task:
            return None, "任务不存在"

        can_proceed, error = InspectionService._check_can_inspect(task, inspector_id)
        if not can_proceed:
            return None, error

        if task.status == models.TaskStatus.WAITING_INSPECTION:
            success, error = WorkflowService.try_claim(
                db, task, inspector_id, inspector_name, models.TaskStatus.WAITING_INSPECTION
            )
            if not success:
                return None, error

        # ------------------------------------------------------------------
        # 查询/创建 PENDING inspection —— 配合唯一约束 + IntegrityError 重试
        # 保证并发下永远只有 1 条 (task_id, inspector_id, result=PENDING)
        # ------------------------------------------------------------------
        for attempt in range(2):
            existing = (
                db.query(models.Inspection)
                .filter(
                    models.Inspection.task_id == task_id,
                    models.Inspection.inspector_id == inspector_id,
                    models.Inspection.result == models.InspectionResult.PENDING,
                )
                .first()
            )

            if existing:
                existing.result = inspection_in.result
                existing.final_annotation = inspection_in.final_annotation
                existing.comment = inspection_in.comment
                existing.score = inspection_in.score
                existing.updated_at = datetime.utcnow()
                inspection = existing
                break

            inspection = models.Inspection(
                task_id=task_id,
                inspector_id=inspector_id,
                inspector_name=inspector_name,
                result=inspection_in.result,
                final_annotation=inspection_in.final_annotation,
                comment=inspection_in.comment,
                score=inspection_in.score,
            )
            db.add(inspection)
            try:
                db.flush()
                break
            except IntegrityError:
                # ----- 并发：另一个线程先创建了 PENDING 记录 -----
                db.rollback()
                # 第 2 次循环会查到 existing，然后 update 它
                continue
        else:
            return None, "提交冲突，请稍后重试"

        InspectionService._apply_status_transition(task, inspection_in.result, inspector_id)

        db.flush()
        return inspection, None

    @staticmethod
    def _check_can_inspect(
        task: models.AnnotationTask,
        inspector_id: int,
    ) -> Tuple[bool, Optional[str]]:
        if task.status == models.TaskStatus.WAITING_INSPECTION:
            if task.claimed_by is None:
                return True, None
            if WorkflowService.is_claim_expired(task.claimed_at):
                return True, None
            if task.claimed_by == inspector_id:
                return True, None
            return False, f"任务已被 {task.claimed_by_name} 领取，请选择其他任务"

        if task.status == models.TaskStatus.INSPECTING:
            if task.claimed_by == inspector_id:
                return True, None
            return False, "任务正在质检中，无法操作"

        return False, "任务状态不允许质检"

    @staticmethod
    def _apply_status_transition(
        task: models.AnnotationTask,
        result: models.InspectionResult,
        inspector_id: int,
    ) -> None:
        if result == models.InspectionResult.PENDING:
            WorkflowService.start_inspection(task)
        elif result == models.InspectionResult.FAIL:
            WorkflowService.fail_inspection(task)
        elif result == models.InspectionResult.PASS:
            WorkflowService.pass_inspection(task)
        elif result == models.InspectionResult.ARBITRATED:
            WorkflowService.arbitrate_inspection(task)

    @staticmethod
    def batch_submit(
        db: Session,
        items: List[schemas.BatchInspectionItem],
        inspector_id: int,
        inspector_name: str,
    ) -> schemas.BatchInspectionResult:
        success_count = 0
        failed_tasks: List[int] = []

        for item in items:
            inspection_in = schemas.InspectionSubmit(
                result=item.result,
                final_annotation=item.final_annotation,
                comment=item.comment,
                score=item.score,
            )
            inspection, error = InspectionService.submit_inspection(
                db, item.task_id, inspection_in, inspector_id, inspector_name
            )
            if inspection and not error:
                success_count += 1
            else:
                failed_tasks.append(item.task_id)

        return schemas.BatchInspectionResult(
            success_count=success_count,
            failed_count=len(failed_tasks),
            failed_tasks=failed_tasks,
        )

    @staticmethod
    def batch_quick_pass(
        db: Session,
        task_ids: List[int],
        inspector_id: int,
        inspector_name: str,
        comment: str = "批量质检通过",
    ) -> schemas.BatchInspectionResult:
        inspection_in = schemas.InspectionSubmit(
            result=models.InspectionResult.PASS,
            comment=comment,
        )

        items = [
            schemas.BatchInspectionItem(
                task_id=tid,
                result=models.InspectionResult.PASS,
                comment=comment,
            )
            for tid in task_ids
        ]

        return InspectionService.batch_submit(db, items, inspector_id, inspector_name)

    @staticmethod
    def get_pending_inspections(
        db: Session,
        inspector_id: int,
        limit: int = 50,
    ) -> List[schemas.TaskListItem]:
        now = datetime.utcnow()
        timeout_threshold = now - timedelta(minutes=CLAIM_TIMEOUT_MINUTES)

        tasks = (
            db.query(models.AnnotationTask)
            .filter(
                models.AnnotationTask.status == models.TaskStatus.WAITING_INSPECTION,
                (
                    (models.AnnotationTask.claimed_by.is_(None))
                    | (models.AnnotationTask.claimed_at < timeout_threshold)
                    | (models.AnnotationTask.claimed_by == inspector_id)
                ),
            )
            .order_by(models.AnnotationTask.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [TaskService._to_task_list_item(db, t) for t in tasks]
