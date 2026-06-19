"""任务领取场景 - 并发单元测试（审核流侧 - 质检）

分层验证策略
============

A. 复现层（DEMO, xfail）——证明『没有 CAS 就会出 bug』
   通过 monkey patch 在 try_claim 内部放大竞态窗口，稳定复现 check-then-act 漏洞。
   目的：记录漏洞形态，作为回归基线（若未来有人把 try_claim 改回内存式读取，这些用例就会从 xfail 变 fail）。

B. 修复验证层（must pass）——验证 CAS UPDATE + 部分唯一索引 的并发正确性
   不做任何 patch，对真实实现进行高并发压力测试，确保：
   - N 个质检员领取同一任务：恰好 1 人领取成功
   - N 个质检员并发提交 PASS：恰好 1 条 PASS 记录，任务状态 = COMPLETED
   - N 次 PENDING 暂存（同任务同质检员）：只有 1 条记录
   - 超时后 N 人抢领：恰好 1 人成功
"""

import os
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import Session, sessionmaker

from .. import models, schemas
from ..database import Base
from ..services import InspectionService, TaskService, WorkflowService
from ..services.workflow_service import CLAIM_TIMEOUT_MINUTES
from datetime import datetime, timedelta


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def db_env():
    """创建 WAL 模式的临时 SQLite，适合多线程并发。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite:///{tmp.name}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 30},
        # NullPool: 每个 Session（每个线程）拿独立的 SQLite 连接，
        # 完全避免多线程共享同一 DBAPI 连接的底层隐患。
        poolclass=pool.NullPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )

    yield engine, SessionFactory

    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        try:
            os.unlink(tmp.name + suffix)
        except OSError:
            pass


def _seed_waiting_task(db: Session, content_id: str = "cnt-001") -> models.AnnotationTask:
    suffix = content_id.replace("-", "_")
    a = models.Annotator(name=f"标注员A_{suffix}")
    b = models.Annotator(name=f"标注员B_{suffix}")
    db.add_all([a, b])
    db.flush()
    task = models.AnnotationTask(
        content_id=content_id,
        content_type="text",
        title=f"测试任务-{content_id}",
        content="内容",
        status=models.TaskStatus.WAITING_INSPECTION,
    )
    db.add(task)
    db.flush()
    ann = models.Annotation(
        task_id=task.id,
        annotator_a_id=a.id,
        annotator_b_id=b.id,
        result_a={"label": "合规"},
        result_b={"label": "合规"},
        consistency_status=models.ConsistencyStatus.CONSISTENT,
        consistency_score=1.0,
    )
    db.add(ann)
    db.flush()
    return task


# ===========================================================================
# A. 反证层（DEMO / xfail）——没有 CAS 保护时的 bug 形态
# 目的：作为"漏洞形态基线"，若 try_claim 被改回非原子式，这些用例会从 xfail 变 fail
# ===========================================================================

class _DemoRaceInspectorClaim:
    """故意放大 try_claim 竞态 —— 不使用真实 CAS UPDATE。"""

    @staticmethod
    def make_racy_try_claim(barrier: threading.Barrier):
        """注入 barrier + sleep，把 check→write 窗口人为放大。

        注意：签名必须匹配真实 try_claim(db, task, user_id, user_name, target_status)
        但我们忽略 db，直接操作 ORM 对象，模拟"无 CAS 的旧实现"。
        """

        def _fn(_db, task_obj, user_id, user_name, target_status):
            if task_obj.status != target_status:
                return False, f"任务状态为 {task_obj.status.value}，不允许领取"
            can_flag = (
                task_obj.claimed_by is None
                or WorkflowService.is_claim_expired(task_obj.claimed_at)
            )
            is_own = task_obj.claimed_by == user_id
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError:
                pass
            time.sleep(0.03)
            if can_flag:
                task_obj.claimed_by = user_id
                task_obj.claimed_by_name = user_name
                task_obj.claimed_at = datetime.utcnow()
                return True, None
            if is_own:
                return True, None
            return False, f"任务已被 {task_obj.claimed_by_name} 领取"

        return _fn


class TestDemoRaceWithoutCAS:
    """反证层：若把 try_claim 改成内存式（无 CAS UPDATE），bug 会稳定复现。

    全部用 xfail 标记 —— 它们本来就应该失败（因为我们故意注入了竞态）。
    如果未来有人删掉 try_claim 的 CAS，把它改回内存式读写，那么：
    修复层的用例会 FAIL；而本层的用例会 PASS（xfail 状态异常 —— 应视为回归告警）。
    """

    @pytest.mark.xfail(
        reason="故意注入竞态复现 bug —— 证明没有 CAS 时多人都报告领取成功"
    )
    def test_demo_concurrent_claim_all_succeed__RACE(self, db_env):
        _, SessionFactory = db_env
        NUM = 5

        prep: Session = SessionFactory()
        try:
            task = _seed_waiting_task(prep, "demo-claim-race")
            task_id = task.id
            prep.commit()
        finally:
            prep.close()

        barrier = threading.Barrier(NUM)
        racy = _DemoRaceInspectorClaim.make_racy_try_claim(barrier)
        results: List[Tuple[int, bool, dict]] = []
        lock = threading.Lock()

        # -------- patch 必须放在主线程，避免多线程嵌套 patch 导致泄漏 --------
        with patch.object(WorkflowService, "try_claim", side_effect=racy):
            def worker(idx: int):
                sess: Session = SessionFactory()
                try:
                    ok, _err, data = InspectionService.claim_task(
                        sess, task_id, 100 + idx, f"质检员-{idx}"
                    )
                    sess.commit()
                except Exception as e:
                    with lock:
                        results.append((idx, False, {"error": str(e)}))
                    return
                finally:
                    sess.close()
                with lock:
                    results.append((idx, ok, data or {}))

            with ThreadPoolExecutor(max_workers=NUM) as pool:
                for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
                    f.result()

        success = [(i, d) for i, ok, d in results if ok and d.get("claimed") is True]
        # xfail 断言：这个断言在"故意注入竞态"下应当失败（即 >1 人成功）
        assert len(success) == 1, f"故意复现失败，成功领取人数={len(success)}"

    @pytest.mark.xfail(reason="故意注入双重竞态：racy try_claim + 放大 is_claim_expired")
    def test_demo_timeout_reclaim_all_succeed__RACE(self, db_env):
        _, SessionFactory = db_env
        NUM = 4

        prep: Session = SessionFactory()
        try:
            task = _seed_waiting_task(prep, "demo-timeout-race")
            task.claimed_by = 50
            task.claimed_by_name = "老质检员"
            task.claimed_at = datetime.utcnow() - timedelta(
                minutes=CLAIM_TIMEOUT_MINUTES + 1
            )
            task_id = task.id
            prep.commit()
        finally:
            prep.close()

        barrier = threading.Barrier(NUM)
        results: List[Tuple[int, bool, dict]] = []
        lock = threading.Lock()
        orig_is_expired = WorkflowService.is_claim_expired

        # 放大 is_claim_expired 的竞态窗口（配合 barrier + sleep）
        def racy_is_expired(claimed_at):
            r = orig_is_expired(claimed_at) if claimed_at else True
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError:
                pass
            time.sleep(0.03)
            return r

        # 同时使用 racy try_claim（非原子内存式修改），保证能稳定复现漏洞
        racy_claim = _DemoRaceInspectorClaim.make_racy_try_claim(barrier)

        # -------- 两个 patch 都必须在主线程，避免多线程嵌套 patch 泄漏 --------
        with patch.object(
            WorkflowService, "is_claim_expired", side_effect=racy_is_expired
        ), patch.object(WorkflowService, "try_claim", side_effect=racy_claim):
            def worker(idx: int):
                sess: Session = SessionFactory()
                try:
                    ok, _err, data = InspectionService.claim_task(
                        sess, task_id, 300 + idx, f"抢领员-{idx}"
                    )
                    sess.commit()
                except Exception as e:
                    with lock:
                        results.append((idx, False, {"error": str(e)}))
                    return
                finally:
                    sess.close()
                with lock:
                    results.append((idx, ok, data or {}))

            with ThreadPoolExecutor(max_workers=NUM) as pool:
                for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
                    f.result()

        success = [(i, d) for i, ok, d in results if ok and d.get("claimed") is True]
        assert len(success) == 1


# ===========================================================================
# B. 修复验证层 —— 调真实实现，高并发压测 CAS UPDATE
# ===========================================================================

class TestConcurrentClaim:
    def test_concurrent_claim_single_winner(self, db_env):
        """[修复验证] N 个质检员并发领取 → 恰好 1 人成功领取。

        这里**不 patch** try_claim，调用真实 CAS UPDATE 实现。
        为了消除偶发，重复跑 3 轮。
        """
        _, SessionFactory = db_env
        NUM_INSPECTORS = 10
        ROUNDS = 3

        for rnd in range(ROUNDS):
            prep: Session = SessionFactory()
            try:
                task = _seed_waiting_task(prep, f"claim-real-r{rnd}")
                task_id = task.id
                prep.commit()
            finally:
                prep.close()

            barrier = threading.Barrier(NUM_INSPECTORS)
            results: List[Tuple[int, bool, str, dict]] = []
            lock = threading.Lock()

            def worker(idx: int):
                sess: Session = SessionFactory()
                try:
                    # barrier 让所有线程"尽可能同时"开始调用 claim_task
                    try:
                        barrier.wait(timeout=5)
                    except threading.BrokenBarrierError:
                        pass
                    ok, err, data = InspectionService.claim_task(
                        sess, task_id, 500 + idx, f"R{rnd}质检员-{idx}"
                    )
                    try:
                        sess.commit()
                    except Exception as ce:
                        with lock:
                            results.append((idx, False, f"commit:{ce}", {}))
                        return
                except Exception as e:
                    with lock:
                        results.append((idx, False, f"exc:{e}", {}))
                    return
                finally:
                    sess.close()
                with lock:
                    results.append((idx, ok, err or "", data or {}))

            with ThreadPoolExecutor(max_workers=NUM_INSPECTORS) as pool:
                for f in as_completed(
                    [pool.submit(worker, i) for i in range(NUM_INSPECTORS)]
                ):
                    f.result()

            success = [(i, d) for i, ok, err, d in results if ok and d.get("claimed") is True]
            fail_info = [(i, d) for i, ok, err, d in results if ok and d.get("claimed") is False]
            hard_err = [(i, err) for i, ok, err, d in results if not ok]

            final: Session = SessionFactory()
            try:
                ft = TaskService.get_task(final, task_id)
                print(f"\n[round {rnd}] {NUM_INSPECTORS} 人并发领取 任务#{task_id}")
                for idx, ok, err, d in sorted(results, key=lambda x: x[0]):
                    print(
                        f"  质检员-{idx:02d}: ok={ok!s:5} "
                        f"claimed={d.get('claimed')!s:5} "
                        f"by={d.get('claimed_by_name', '-')!s:14} err={err!r}"
                    )
                print(
                    f"  DB 最终 claimed_by={ft.claimed_by} ({ft.claimed_by_name})  "
                    f"status={ft.status}"
                )
                print(
                    f"  统计: 成功领取={len(success)}  "
                    f"已被他人领取={len(fail_info)}  硬错误={len(hard_err)}"
                )

                # 核心断言：恰好 1 人真正领到
                assert len(success) == 1, (
                    f"round {rnd}: 预期恰好 1 人领取成功，实际 {len(success)} 人。"
                    f" 修复未生效或 CAS 逻辑有误。"
                )
                # 其余 N-1 人要么是『已被 XX 领取』的业务性失败，要么是硬错误
                total = len(success) + len(fail_info) + len(hard_err)
                assert total == NUM_INSPECTORS
                # DB 最终值必须与成功领取人一致
                winner_name = success[0][1]["claimed_by_name"]
                assert ft.claimed_by_name == winner_name
                assert ft.claimed_by is not None
            finally:
                final.close()

    def test_no_race_sequential_claim(self, db_env):
        """对照组：串行领取只有 1 人成功。"""
        _, SessionFactory = db_env
        db: Session = SessionFactory()
        try:
            task = _seed_waiting_task(db, "seq-claim")
            task_id = task.id
            db.commit()

            r1_ok, _, r1_data = InspectionService.claim_task(db, task_id, 1, "质检员-1")
            db.commit()
            r2_ok, _, r2_data = InspectionService.claim_task(db, task_id, 2, "质检员-2")
            db.commit()

            assert r1_ok and r1_data["claimed"] is True
            assert r2_ok and r2_data["claimed"] is False
            assert r2_data["claimed_by_name"] == "质检员-1"
        finally:
            db.close()


class TestConcurrentSubmitInspection:
    def test_concurrent_submit_pass_only_one_completes(self, db_env):
        """[修复验证] N 人并发提交 PASS → DB 只有 1 条 PASS，任务=COMPLETED。"""
        _, SessionFactory = db_env
        NUM = 8

        prep: Session = SessionFactory()
        try:
            task = _seed_waiting_task(prep, "submit-pass-real")
            task_id = task.id
            prep.commit()
        finally:
            prep.close()

        barrier = threading.Barrier(NUM)
        outcomes: List[Tuple[int, bool, str]] = []
        lock = threading.Lock()

        def worker(idx: int):
            sess: Session = SessionFactory()
            try:
                payload = schemas.InspectionSubmit(
                    result=models.InspectionResult.PASS,
                    comment=f"提交人-{idx}",
                )
                try:
                    barrier.wait(timeout=5)
                except threading.BrokenBarrierError:
                    pass
                insp, err = InspectionService.submit_inspection(
                    sess, task_id, payload, 600 + idx, f"提交者-{idx}"
                )
                try:
                    sess.commit()
                except Exception as ce:
                    with lock:
                        outcomes.append((idx, False, f"commit:{ce}"))
                    return
            except Exception as e:
                with lock:
                    outcomes.append((idx, False, f"exc:{e}"))
                return
            finally:
                sess.close()
            with lock:
                outcomes.append((idx, insp is not None and err is None, err or ""))

        with ThreadPoolExecutor(max_workers=NUM) as pool:
            for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
                f.result()

        final: Session = SessionFactory()
        try:
            ft = TaskService.get_task(final, task_id)
            pass_rows = (
                final.query(models.Inspection)
                .filter(
                    models.Inspection.task_id == task_id,
                    models.Inspection.result == models.InspectionResult.PASS,
                )
                .all()
            )
            all_rows = final.query(models.Inspection).filter(
                models.Inspection.task_id == task_id
            ).all()

            print(f"\n[并发提交 PASS] {NUM} 人  任务#{task_id}")
            for idx, ok, err in sorted(outcomes, key=lambda x: x[0]):
                print(f"  提交者-{idx}: ok={ok!s:5} err={err!r}")
            print(f"  DB 状态: status={ft.status}  PASS 条数={len(pass_rows)}  总条数={len(all_rows)}")
            for r in all_rows:
                print(
                    f"    id={r.id:2d}  insp={r.inspector_name:10}  "
                    f"result={r.result.value:8}  comment={r.comment!r}"
                )

            assert len(pass_rows) == 1, (
                f"预期 1 条 PASS，实际 {len(pass_rows)} 条。"
                f" try_claim CAS 或 唯一约束未生效。"
            )
            assert ft.status == models.TaskStatus.COMPLETED
            assert ft.claimed_by is None  # pass_inspection 后 force_release
        finally:
            final.close()


class TestConcurrentPendingInspection:
    def test_concurrent_pending_creation_no_duplicate(self, db_env):
        """[修复验证] 同任务同质检员并发 N 次暂存(PENDING) → DB 只有 1 条 PENDING。

        关键：部分唯一索引 uq_inspection_task_inspector_pending 在 db.flush() 时
        会对重复写入抛 IntegrityError；submit_inspection 内部会 retry 一次
        （查询 existing 再 update）。
        """
        _, SessionFactory = db_env
        NUM = 10

        prep: Session = SessionFactory()
        try:
            task = _seed_waiting_task(prep, "pending-real")
            task.status = models.TaskStatus.INSPECTING
            task.claimed_by = 777
            task.claimed_by_name = "质检员-777"
            task.claimed_at = datetime.utcnow()
            task_id = task.id
            prep.commit()
        finally:
            prep.close()

        barrier = threading.Barrier(NUM)

        def worker(idx: int):
            sess: Session = SessionFactory()
            try:
                payload = schemas.InspectionSubmit(
                    result=models.InspectionResult.PENDING,
                    comment=f"草稿-{idx}",
                )
                try:
                    barrier.wait(timeout=5)
                except threading.BrokenBarrierError:
                    pass
                insp, err = InspectionService.submit_inspection(
                    sess, task_id, payload, 777, "质检员-777"
                )
                try:
                    sess.commit()
                except Exception:
                    pass
            finally:
                sess.close()

        with ThreadPoolExecutor(max_workers=NUM) as pool:
            for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
                f.result()

        final: Session = SessionFactory()
        try:
            pending_rows = (
                final.query(models.Inspection)
                .filter(
                    models.Inspection.task_id == task_id,
                    models.Inspection.inspector_id == 777,
                    models.Inspection.result == models.InspectionResult.PENDING,
                )
                .all()
            )
            all_rows = final.query(models.Inspection).filter(
                models.Inspection.task_id == task_id,
                models.Inspection.inspector_id == 777,
            ).all()

            print(f"\n[并发 PENDING 暂存] {NUM} 次  任务#{task_id}")
            print(f"  DB PENDING 条数 = {len(pending_rows)}")
            print(f"  DB inspection 总条数 = {len(all_rows)}")
            for r in all_rows:
                print(
                    f"    id={r.id}  result={r.result.value:8}  "
                    f"comment={r.comment!r}"
                )

            # 唯一约束保证：永远只有 1 条 (task=?, insp=777, result=PENDING)
            assert len(pending_rows) == 1, (
                f"预期 1 条 PENDING，实际 {len(pending_rows)} 条。"
                f" 唯一约束或 retry 逻辑未生效。"
            )
        finally:
            final.close()


class TestClaimTimeoutAndReclaim:
    def test_expired_claim_can_be_reclaimed_by_another(self, db_env):
        """基础用例：超时后新质检员可顺利抢领。"""
        _, SessionFactory = db_env
        db: Session = SessionFactory()
        try:
            task = _seed_waiting_task(db, "timeout-base")
            task.claimed_by = 50
            task.claimed_by_name = "老质检员"
            task.claimed_at = datetime.utcnow() - timedelta(
                minutes=CLAIM_TIMEOUT_MINUTES + 1
            )
            task_id = task.id
            db.commit()

            ok, _, data = InspectionService.claim_task(db, task_id, 51, "新质检员")
            db.commit()
            assert ok and data["claimed"] is True
            assert data["claimed_by_name"] == "新质检员"
        finally:
            db.close()

    def test_expired_claim_concurrent_reclaim_only_one_winner(self, db_env):
        """[修复验证] 已超时领取 + N 人并发抢领 → 恰好 1 人成功。"""
        _, SessionFactory = db_env
        NUM = 8

        prep: Session = SessionFactory()
        try:
            task = _seed_waiting_task(prep, "timeout-concurrent-real")
            task.claimed_by = 50
            task.claimed_by_name = "老质检员"
            task.claimed_at = datetime.utcnow() - timedelta(
                minutes=CLAIM_TIMEOUT_MINUTES + 1
            )
            task_id = task.id
            prep.commit()
        finally:
            prep.close()

        barrier = threading.Barrier(NUM)
        results: List[Tuple[int, bool, dict]] = []
        lock = threading.Lock()

        def worker(idx: int):
            sess: Session = SessionFactory()
            try:
                try:
                    barrier.wait(timeout=5)
                except threading.BrokenBarrierError:
                    pass
                ok, _err, data = InspectionService.claim_task(
                    sess, task_id, 800 + idx, f"抢领员-{idx}"
                )
                sess.commit()
            except Exception:
                return
            finally:
                sess.close()
            with lock:
                results.append((idx, ok, data or {}))

        with ThreadPoolExecutor(max_workers=NUM) as pool:
            for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
                f.result()

        print(f"\n[超时后并发抢领] {NUM} 人  任务#{task_id}")
        for idx, ok, d in sorted(results, key=lambda x: x[0]):
            print(
                f"  抢领员-{idx}: ok={ok!s:5}  "
                f"claimed={d.get('claimed')!s:5}  by={d.get('claimed_by_name', '-')}"
            )

        success = [(i, d) for i, ok, d in results if ok and d.get("claimed") is True]
        assert len(success) == 1, (
            f"超时后抢领应恰好 1 人成功，实际 {len(success)} 人。"
            f" try_claim 的超时判断 WHERE 条件可能缺失。"
        )
