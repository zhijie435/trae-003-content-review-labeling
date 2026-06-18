from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .models import UserRole, TaskStatus, AnnotationResult, QualityStatus


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.ANNOTATOR


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TaskBase(BaseModel):
    title: str
    content: str
    content_type: str = "text"
    batch_id: Optional[str] = None
    priority: int = 0


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    annotations: List["AnnotationResponse"] = []
    quality_checks: List["QualityCheckResponse"] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
    page: int
    page_size: int


class AnnotationBase(BaseModel):
    task_id: int
    result: AnnotationResult
    remark: Optional[str] = None
    tags: Optional[str] = None


class AnnotationCreate(AnnotationBase):
    pass


class AnnotationResponse(AnnotationBase):
    id: int
    annotator_id: int
    annotator: Optional[UserResponse] = None
    annotation_index: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QualityCheckBase(BaseModel):
    task_id: int
    status: QualityStatus = QualityStatus.PENDING
    final_result: Optional[AnnotationResult] = None
    remark: Optional[str] = None


class QualityCheckCreate(QualityCheckBase):
    pass


class QualityCheckUpdate(BaseModel):
    status: Optional[QualityStatus] = None
    final_result: Optional[AnnotationResult] = None
    remark: Optional[str] = None


class QualityCheckResponse(QualityCheckBase):
    id: int
    checker_id: int
    checker: Optional[UserResponse] = None
    is_sampled: bool
    sample_batch_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SampleBatchBase(BaseModel):
    name: str
    batch_type: str = "random"
    sample_ratio: float = 0.1


class SampleBatchCreate(SampleBatchBase):
    pass


class SampleBatchResponse(SampleBatchBase):
    id: int
    sample_count: int
    total_count: int
    status: str
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DoubleAnnotationStats(BaseModel):
    total_tasks: int
    consistent_tasks: int
    inconsistent_tasks: int
    consistency_rate: float
    in_quality_check: int
    quality_checked: int


class AssignTaskRequest(BaseModel):
    annotator_ids: List[int]
