"""调试 CAS UPDATE 在 SQLite 多线程下的 rowcount 行为。"""
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, update, or_
from sqlalchemy.orm import sessionmaker, Session

from app.models import Base, AnnotationTask, TaskStatus


tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
db_url = f"sqlite:///{tmp.name}"

engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 30})

@event.listens_for(engine, "connect")
def _pragmas(conn, rec):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA busy_timeout=30000;")
    cur.close()

Base.metadata.create_all(engine)
SF = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def seed():
    s: Session = SF()
    try:
        t = AnnotationTask(
            content_id="dbg-1",
            content_type="text",
            title="dbg",
            content="xxx",
            status=TaskStatus.WAITING_INSPECTION,
        )
        s.add(t); s.flush(); s.commit()
        return t.id
    finally:
        s.close()

task_id = seed()
print(f"[seed] task_id={task_id}")

NUM = 5
barrier = threading.Barrier(NUM)
CLAIM_MINS = 30

def worker(idx):
    s: Session = SF()
    user_id = 900 + idx
    user_name = f"U-{idx}"
    try:
        task = s.query(AnnotationTask).filter(AnnotationTask.id == task_id).first()
        assert task, "task gone"
        print(f"[T{idx}] before: claimed_by={task.claimed_by}")

        try:
            barrier.wait(timeout=5)
        except threading.BrokenBarrierError:
            pass
        time.sleep(0.01)

        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=CLAIM_MINS)

        # 真实 SQL 打印
        print(f"[T{idx}] UPDATE WHERE status={TaskStatus.WAITING_INSPECTION.value} "
              f"AND (claimed_by IS NULL OR claimed_at < {cutoff} OR claimed_by={user_id})")

        stmt = (
            update(AnnotationTask)
            .where(
                AnnotationTask.id == task_id,
                AnnotationTask.status == TaskStatus.WAITING_INSPECTION,
                or_(
                    AnnotationTask.claimed_by.is_(None),
                    AnnotationTask.claimed_at < cutoff,
                    AnnotationTask.claimed_by == user_id,
                ),
            )
            .values(
                claimed_by=user_id,
                claimed_by_name=user_name,
                claimed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)  # <-- 改为False，排除干扰
        )
        result = s.execute(stmt)
        s.flush()
        affected = result.rowcount
        print(f"[T{idx}] >>> rowcount = {affected} <<< claimed_by(内存)={task.claimed_by}")

        s.commit()

        # 读最终 DB 值
        s2: Session = SF()
        try:
            ft = s2.query(AnnotationTask).filter(AnnotationTask.id == task_id).first()
            print(f"[T{idx}] DB after commit: claimed_by={ft.claimed_by} ({ft.claimed_by_name})")
        finally:
            s2.close()

        return (idx, affected, task.claimed_by)
    except Exception as e:
        print(f"[T{idx}] EXC: {e!r}")
        import traceback; traceback.print_exc()
        return (idx, -1, None)
    finally:
        s.close()


with ThreadPoolExecutor(max_workers=NUM) as pool:
    for f in as_completed([pool.submit(worker, i) for i in range(NUM)]):
        pass

# final
fs: Session = SF()
try:
    t = fs.query(AnnotationTask).filter(AnnotationTask.id == task_id).first()
    print(f"\n[FINAL DB] task_id={t.id} claimed_by={t.claimed_by} ({t.claimed_by_name}) "
          f"claimed_at={t.claimed_at}")
finally:
    fs.close()

try:
    os.unlink(tmp.name)
    for sfx in ("-wal", "-shm"):
        try: os.unlink(tmp.name + sfx)
        except: pass
except: pass
