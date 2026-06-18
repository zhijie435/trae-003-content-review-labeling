export enum AnnotationType {
  TEXT = 'text',
  IMAGE = 'image',
}

export enum AnnotationStatus {
  PENDING = 'pending',
  ANNOTATED = 'annotated',
  REVIEWED = 'reviewed',
}

export enum AnnotationResult {
  PASS = 'pass',
  VIOLATION = 'violation',
  SUSPICIOUS = 'suspicious',
}

export interface Annotation {
  id: number;
  type: AnnotationType;
  content?: string;
  imageUrl?: string;
  result?: AnnotationResult;
  tags?: string;
  remark?: string;
  status: AnnotationStatus;
  annotator?: string;
  reviewer?: string;
  createdAt: string;
  updatedAt: string;
}
