import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || isNaN(value)) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

export const TASK_STATUS_LABEL: Record<string, string> = {
  pending: "待标注",
  double_annotating: "双标注中",
  waiting_inspection: "待质检",
  inspecting: "质检中",
  completed: "已完成",
};

export const CONSISTENCY_LABEL: Record<string, string> = {
  consistent: "一致",
  inconsistent: "不一致",
  partial: "部分一致",
  unchecked: "未检测",
};

export const INSPECTION_LABEL: Record<string, string> = {
  pass: "通过",
  fail: "不通过",
  arbitrated: "已仲裁",
  pending: "待质检",
};
