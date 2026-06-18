"use client";

import { cn } from "@/lib/utils";
import { CONSISTENCY_LABEL, INSPECTION_LABEL, TASK_STATUS_LABEL } from "@/lib/utils";
import type { ConsistencyStatus, InspectionResult, TaskStatus } from "@/lib/types";

export function StatusBadge({
  status,
  type = "task",
}: {
  status: string | null | undefined;
  type?: "task" | "consistency" | "inspection";
}) {
  if (!status) return <span className="text-slate-400 text-xs">-</span>;

  const label =
    type === "task"
      ? TASK_STATUS_LABEL[status] || status
      : type === "consistency"
      ? CONSISTENCY_LABEL[status] || status
      : INSPECTION_LABEL[status] || status;

  const map: Record<string, string> = {
    pending: "bg-slate-100 text-slate-700",
    double_annotating: "bg-blue-100 text-blue-700",
    waiting_inspection: "bg-amber-100 text-amber-700",
    inspecting: "bg-purple-100 text-purple-700",
    completed: "bg-emerald-100 text-emerald-700",
    consistent: "bg-emerald-100 text-emerald-700",
    inconsistent: "bg-red-100 text-red-700",
    partial: "bg-amber-100 text-amber-700",
    unchecked: "bg-slate-100 text-slate-500",
    pass: "bg-emerald-100 text-emerald-700",
    fail: "bg-red-100 text-red-700",
    arbitrated: "bg-blue-100 text-blue-700",
  };

  return (
    <span className={cn("badge", map[status] || "bg-slate-100 text-slate-700")}>
      {label}
    </span>
  );
}
