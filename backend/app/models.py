from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float, JSON
from sqlalchemy.orm import relationship

from .database import Base


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    DOUBLE_ANNOTATING = "double_annotating"
    WAITING_INSPECTION = "waiting_inspection"
    INSPECTING = "inspecting"
    COMPLETED = "completed"


class ConsistencyStatus(str, PyEnum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    PARTIAL = "partial"
    UNCHECKED = "unchecked"


class InspectionResult(str, PyEnum):
    PASS = "pass"
    FAIL = "fail"
    ARBITRATED = "arbitrated"
    PENDING = "pending"


class Annotator(Base):
    __tablename__ = "annotators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    annotations_a = relationship("Annotation", foreign_keys="Annotation.annotator_a_id", back_populates="annotator_a")
    annotations_b = relationship("Annotation", foreign_keys="Annotation.annotator_b_id", back_populates="annotator_b")


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(String(100), unique=True, nullable=False)
    content_type = Column(String(20), default="text")
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    extra = Column(JSON, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    claimed_by = Column(Integer, nullable=True)
    claimed_by_name = Column(String(50), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    annotations = relationship("Annotation", back_populates="task", uselist=False)
    inspections = relationship("Inspection", back_populates="task")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("annotation_tasks.id"), unique=True, nullable=False)
    annotator_a_id = Column(Integer, ForeignKey("annotators.id"), nullable=False)
    annotator_b_id = Column(Integer, ForeignKey("annotators.id"), nullable=False)
    result_a = Column(JSON, nullable=False)
    result_b = Column(JSON, nullable=False)
    annotated_at_a = Column(DateTime, nullable=True)
    annotated_at_b = Column(DateTime, nullable=True)
    consistency_status = Column(Enum(ConsistencyStatus), default=ConsistencyStatus.UNCHECKED)
    consistency_score = Column(Float, nullable=True)
    diff_detail = Column(JSON, nullable=True)

    task = relationship("AnnotationTask", back_populates="annotations")
    annotator_a = relationship("Annotator", foreign_keys=[annotator_a_id], back_populates="annotations_a")
    annotator_b = relationship("Annotator", foreign_keys=[annotator_b_id], back_populates="annotations_b")


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("annotation_tasks.id"), nullable=False)
    inspector_id = Column(Integer, nullable=False)
    inspector_name = Column(String(50), nullable=False)
    result = Column(Enum(InspectionResult), default=InspectionResult.PENDING)
    final_annotation = Column(JSON, nullable=True)
    comment = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("AnnotationTask", back_populates="inspections")


class SamplingBatch(Base):
    __tablename__ = "sampling_batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sample_count = Column(Integer, nullable=False)
    sample_ratio = Column(Float, nullable=True)
    strategy = Column(String(50), default="random")
    consistency_filter = Column(String(20), nullable=True)
    task_ids = Column(JSON, nullable=False)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
