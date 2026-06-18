export type TaskStatus =
  | "pending"
  | "double_annotating"
  | "waiting_inspection"
  | "inspecting"
  | "completed";

export type ConsistencyStatus = "consistent" | "inconsistent" | "partial" | "unchecked";

export type InspectionResult = "pass" | "fail" | "arbitrated" | "pending";

export interface TaskListItem {
  id: number;
  content_id: string;
  title: string;
  content_type: string;
  status: TaskStatus;
  consistency_status: ConsistencyStatus | null;
  consistency_score: number | null;
  annotator_a_name: string | null;
  annotator_b_name: string | null;
  inspection_result: InspectionResult | null;
  updated_at: string;
}

export interface TaskListResponse {
  items: TaskListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnnotationResult {
  risk_level: string;
  category: string;
  suggestion: string;
}

export interface AnnotatorOut {
  id: number;
  name: string;
  avatar: string | null;
  created_at: string;
}

export interface AnnotationOut {
  id: number;
  task_id: number;
  annotator_a_id: number;
  annotator_b_id: number;
  annotator_a: AnnotatorOut | null;
  annotator_b: AnnotatorOut | null;
  result_a: AnnotationResult;
  result_b: AnnotationResult;
  annotated_at_a: string | null;
  annotated_at_b: string | null;
  consistency_status: ConsistencyStatus;
  consistency_score: number | null;
  diff_detail: Record<string, { a: string; b: string }> | null;
}

export interface AnnotationTaskDetail {
  id: number;
  content_id: string;
  content_type: string;
  title: string;
  content: string;
  extra: Record<string, any> | null;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  annotations: AnnotationOut | null;
}

export interface InspectionOut {
  id: number;
  task_id: number;
  inspector_id: number;
  inspector_name: string;
  result: InspectionResult;
  final_annotation: AnnotationResult | null;
  comment: string | null;
  score: number | null;
  created_at: string;
  updated_at: string;
}

export interface InspectionSubmit {
  result: InspectionResult;
  final_annotation?: AnnotationResult;
  comment?: string;
  score?: number;
}

export interface SamplingBatchOut {
  id: number;
  name: string;
  description: string | null;
  sample_count: number;
  strategy: string;
  consistency_filter: string | null;
  task_ids: number[];
  created_by: string;
  created_at: string;
}

export interface SamplingRequest {
  name: string;
  description?: string;
  sample_count: number;
  strategy: string;
  consistency_filter?: ConsistencyStatus;
  created_by: string;
}

export interface BatchInspectionResult {
  success_count: number;
  failed_count: number;
  failed_tasks: number[];
}

export interface SamplingBatchStats {
  batch_id: number;
  batch_name: string;
  total_tasks: number;
  inspected_count: number;
  pending_count: number;
  pass_count: number;
  fail_count: number;
  arbitrated_count: number;
  pass_rate: number;
  misjudgment_rate: number;
  inconsistent_count: number;
  consistent_count: number;
  partial_count: number;
}

export interface StatisticsOut {
  total_tasks: number;
  double_annotated: number;
  waiting_inspection: number;
  inspected: number;
  consistent_count: number;
  inconsistent_count: number;
  partial_count: number;
  consistency_rate: number;
  pass_count: number;
  fail_count: number;
  arbitrated_count: number;
  pass_rate: number;
  total_sampling_batches: number;
  per_annotator_stats: {
    annotator_id: number;
    name: string;
    total_tasks: number;
    consistent_count: number;
    consistency_rate: number;
  }[];
}
