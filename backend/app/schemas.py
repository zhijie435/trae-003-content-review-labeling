from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOUBLE_ANNOTATING = "double_annotating"
    WAITING_INSPECTION = "waiting_inspection"
    INSPECTING = "inspecting"
    COMPLETED = "completed"


class ConsistencyStatus(str, Enum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    PARTIAL = "partial"
    UNCHECKED = "unchecked"


class InspectionResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ARBITRATED = "arbitrated"
    PENDING = "pending"


class AnnotatorBase(BaseModel):
    name: str
    avatar: Optional[str] = None


class AnnotatorCreate(AnnotatorBase):
    pass


class AnnotatorOut(AnnotatorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnnotationTaskBase(BaseModel):
    content_id: str
    content_type: str = "text"
    title: str
    content: str
    extra: Optional[Dict[str, Any]] = None


class AnnotationTaskCreate(AnnotationTaskBase):
    pass


class AnnotationTaskOut(AnnotationTaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnotationTaskDetail(AnnotationTaskOut):
    annotations: Optional["AnnotationOut"] = None


class AnnotationBase(BaseModel):
    task_id: int
    annotator_a_id: int
    annotator_b_id: int
    result_a: Dict[str, Any]
    result_b: Dict[str, Any]


class AnnotationCreate(AnnotationBase):
    pass


class AnnotationOut(BaseModel):
    id: int
    task_id: int
    annotator_a_id: int
    annotator_b_id: int
    annotator_a: Optional[AnnotatorOut] = None
    annotator_b: Optional[AnnotatorOut] = None
    result_a: Dict[str, Any]
    result_b: Dict[str, Any]
    annotated_at_a: Optional[datetime] = None
    annotated_at_b: Optional[datetime] = None
    consistency_status: ConsistencyStatus
    consistency_score: Optional[float] = None
    diff_detail: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class InspectionBase(BaseModel):
    task_id: int
    inspector_id: int
    inspector_name: str


class InspectionCreate(InspectionBase):
    pass


class InspectionSubmit(BaseModel):
    result: InspectionResult
    final_annotation: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    score: Optional[int] = Field(None, ge=0, le=100)


class InspectionOut(InspectionBase):
    id: int
    result: InspectionResult
    final_annotation: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    score: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SamplingRequest(BaseModel):
    name: str
    description: Optional[str] = None
    sample_count: int = Field(None, gt=0)
    sample_ratio: Optional[float] = Field(None, gt=0, le=1)
    strategy: str = "random"
    consistency_filter: Optional[ConsistencyStatus] = None
    created_by: str

    @model_validator(mode="after")
    def check_count_or_ratio(self):
        if self.sample_count is None and self.sample_ratio is None:
            raise ValueError("必须指定 sample_count 或 sample_ratio")
        if self.sample_count is not None and self.sample_ratio is not None:
            raise ValueError("不能同时指定 sample_count 和 sample_ratio")
        return self


class SamplingBatchOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sample_count: int
    sample_ratio: Optional[float] = None
    strategy: str
    consistency_filter: Optional[str] = None
    task_ids: List[int]
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskListItem(BaseModel):
    id: int
    content_id: str
    title: str
    content_type: str
    status: TaskStatus
    consistency_status: Optional[ConsistencyStatus] = None
    consistency_score: Optional[float] = None
    annotator_a_name: Optional[str] = None
    annotator_b_name: Optional[str] = None
    inspection_result: Optional[InspectionResult] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: List[TaskListItem]
    total: int
    page: int
    page_size: int


class BatchInspectionItem(BaseModel):
    task_id: int
    result: InspectionResult
    final_annotation: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    score: Optional[int] = Field(None, ge=0, le=100)


class BatchInspectionRequest(BaseModel):
    items: List[BatchInspectionItem]
    inspector_id: int = 1
    inspector_name: str = "质检员-孙丽"


class BatchInspectionResult(BaseModel):
    success_count: int
    failed_count: int
    failed_tasks: List[int]


class SamplingBatchStats(BaseModel):
    batch_id: int
    batch_name: str
    total_tasks: int
    inspected_count: int
    pending_count: int
    pass_count: int
    fail_count: int
    arbitrated_count: int
    pass_rate: float
    misjudgment_rate: float
    inconsistent_count: int
    consistent_count: int
    partial_count: int


class StatisticsOut(BaseModel):
    total_tasks: int
    double_annotated: int
    waiting_inspection: int
    inspected: int
    consistent_count: int
    inconsistent_count: int
    partial_count: int
    consistency_rate: float
    pass_count: int
    fail_count: int
    arbitrated_count: int
    pass_rate: float
    total_sampling_batches: int
    per_annotator_stats: List[Dict[str, Any]]


AnnotationTaskDetail.model_rebuild()
