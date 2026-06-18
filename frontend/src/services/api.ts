import axios from 'axios';
import type { Annotation, AnnotationType, AnnotationResult } from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export const annotationApi = {
  getList: (type?: AnnotationType) =>
    api.get<Annotation[]>('/annotations', { params: type ? { type } : {} }),

  getReviewList: () =>
    api.get<Annotation[]>('/annotations/review'),

  getDetail: (id: number) =>
    api.get<Annotation>(`/annotations/${id}`),

  createText: (data: {
    type: AnnotationType.TEXT;
    content: string;
    result?: AnnotationResult;
    tags?: string;
    remark?: string;
    annotator?: string;
  }) => api.post<Annotation>('/annotations', data),

  createImage: (data: {
    type: AnnotationType.IMAGE;
    imageUrl: string;
    content?: string;
    result?: AnnotationResult;
    tags?: string;
    remark?: string;
    annotator?: string;
  }) => api.post<Annotation>('/annotations', data),

  update: (id: number, data: {
    result?: AnnotationResult;
    tags?: string;
    remark?: string;
    annotator?: string;
    reviewer?: string;
  }) => api.patch<Annotation>(`/annotations/${id}`, data),

  remove: (id: number) =>
    api.delete(`/annotations/${id}`),

  seed: () =>
    api.get<{ text: number; image: number }>('/annotations/seed'),
};

export default api;
