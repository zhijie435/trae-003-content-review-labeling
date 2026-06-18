import { AnnotationType, AnnotationStatus, AnnotationResult } from '../types';

export const ANNOTATION_TYPE_MAP: Record<AnnotationType, string> = {
  [AnnotationType.TEXT]: '文本',
  [AnnotationType.IMAGE]: '图片',
};

export const ANNOTATION_STATUS_MAP: Record<AnnotationStatus, string> = {
  [AnnotationStatus.PENDING]: '待标注',
  [AnnotationStatus.ANNOTATED]: '已标注',
  [AnnotationStatus.REVIEWED]: '已质检',
};

export const ANNOTATION_STATUS_COLOR: Record<AnnotationStatus, string> = {
  [AnnotationStatus.PENDING]: 'default',
  [AnnotationStatus.ANNOTATED]: 'processing',
  [AnnotationStatus.REVIEWED]: 'success',
};

export const ANNOTATION_RESULT_MAP: Record<AnnotationResult, string> = {
  [AnnotationResult.PASS]: '通过',
  [AnnotationResult.VIOLATION]: '违规',
  [AnnotationResult.SUSPICIOUS]: '疑似',
};

export const ANNOTATION_RESULT_COLOR: Record<AnnotationResult, string> = {
  [AnnotationResult.PASS]: 'success',
  [AnnotationResult.VIOLATION]: 'error',
  [AnnotationResult.SUSPICIOUS]: 'warning',
};
