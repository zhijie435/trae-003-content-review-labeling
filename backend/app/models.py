from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from .database import Base


class UserRole(str, PyEnum):
    ANNOTATOR = "annotator"
    QUALITY_CHECKER = "quality_checker"
    ADMIN = "admin"


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ANNOTATING = "annotating"
    ANNOTATED = "annotated"
    IN_QUALITY_CHECK = "in_quality_check"
    QUALITY_CHECKED = "quality_checked"
    DISPUTED = "disputed"
    COMPLETED = "completed"


class AnnotationResult(str, PyEnum):
    PASS = "pass"
    FAIL = "fail"
    SUSPICIOUS = "suspicious"


class QualityStatus(str, PyEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    DISPUTED = "disputed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(Enum(UserRole), default=UserRole.ANNOTATOR, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    annotations = relationship("Annotation", back_populates="annotator", foreign_keys="Annotation.annotator_id")
    quality_checks = relationship("QualityCheck", back_populates="checker", foreign_keys="QualityCheck.checker_id")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    batch_id = Column(String(100), index=True)
    priority = Column(Integer, default=0)

    annotations = relationship("Annotation", back_populates="task", cascade="all, delete-orphan")
    quality_checks = relationship("QualityCheck", back_populates="task", cascade="all, delete-orphan")
    sample_batch_tasks = relationship("SampleBatchTask", back_populates="task")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    annotator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    result = Column(Enum(AnnotationResult), nullable=False)
    remark = Column(Text)
    tags = Column(String(500))
    annotation_index = Column(Integer, default=1)

    task = relationship("Task", back_populates="annotations")
    annotator = relationship("User", back_populates="annotations", foreign_keys=[annotator_id])

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class QualityCheck(Base):
    __tablename__ = "quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    checker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(QualityStatus), default=QualityStatus.PENDING, nullable=False)
    final_result = Column(Enum(AnnotationResult))
    remark = Column(Text)
    is_sampled = Column(Boolean, default=False)
    sample_batch_id = Column(Integer, ForeignKey("sample_batches.id"))

    task = relationship("Task", back_populates="quality_checks")
    checker = relationship("User", back_populates="quality_checks", foreign_keys=[checker_id])
    sample_batch = relationship("SampleBatch", back_populates="quality_checks")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SampleBatch(Base):
    __tablename__ = "sample_batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    batch_type = Column(String(50), default="random")
    sample_ratio = Column(Float, default=0.1)
    sample_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    status = Column(String(50), default="active")
    created_by = Column(Integer, ForeignKey("users.id"))

    tasks = relationship("SampleBatchTask", back_populates="sample_batch", cascade="all, delete-orphan")
    quality_checks = relationship("QualityCheck", back_populates="sample_batch")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SampleBatchTask(Base):
    __tablename__ = "sample_batch_tasks"

    id = Column(Integer, primary_key=True, index=True)
    sample_batch_id = Column(Integer, ForeignKey("sample_batches.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    is_checked = Column(Boolean, default=False)

    sample_batch = relationship("SampleBatch", back_populates="tasks")
    task = relationship("Task", back_populates="sample_batch_tasks")
