"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import type {
  SamplingBatchOut,
  TaskListItem,
  SamplingBatchStats,
  BatchInspectionResult,
} from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatPercent } from "@/lib/utils";
import {
  ArrowLeft,
  FlaskConical,
  Users,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  CheckSquare,
  Square,
  ChevronDown,
  Zap,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

const STRATEGY_LABEL: Record<string, string> = {
  random: "随机抽样",
  inconsistent_first: "不一致优先",
  high_score_first: "高一致性优先",
};

export default function SamplingDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const batchId = parseInt(params.id as string);

  const [batch, setBatch] = useState<SamplingBatchOut | null>(null);
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [stats, setStats] = useState<SamplingBatchStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [showBatchMenu, setShowBatchMenu] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const fetchData = useCallback(() => {
    if (!batchId) return;
    setLoading(true);
    setTasks([]);
    setStats(null);
    setSelectedIds(new Set());
    Promise.all([
      api.get<SamplingBatchOut>(`/sampling/batches/${batchId}`),
      api.get<TaskListItem[]>(`/sampling/batches/${batchId}/tasks`),
      api.get<SamplingBatchStats>(`/sampling/batches/${batchId}/stats`),
    ])
      .then(([b, t, s]) => {
        setBatch(b.data);
        setTasks(t.data);
        setStats(s.data);
      })
      .finally(() => setLoading(false));
  }, [batchId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        fetchData();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [fetchData]);

  const pendingTasks = tasks.filter((t) => !t.inspection_result || t.inspection_result === "pending");
  const allSelected = pendingTasks.length > 0 && pendingTasks.every((t) => selectedIds.has(t.id));
  const someSelected = selectedIds.size > 0;

  const toggleSelect = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingTasks.map((t) => t.id)));
    }
  };

  const showToast = (type: "success" | "error", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3000);
  };

  const handleBatchQuickPass = async () => {
    if (selectedIds.size === 0) {
      showToast("error", "请先选择要操作的任务");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post<BatchInspectionResult>("/inspections/batch/quick-pass", {
        task_ids: Array.from(selectedIds),
        comment: "抽检批次快捷质检通过",
      });
      showToast("success", `批量提交成功：通过 ${res.data.success_count} 条`);
      setSelectedIds(new Set());
      setShowBatchMenu(false);
      fetchData();
    } catch (e: any) {
      showToast("error", e?.response?.data?.detail || "批量提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBatchQuickFail = async () => {
    if (selectedIds.size === 0) {
      showToast("error", "请先选择要操作的任务");
      return;
    }
    if (!confirm("确定将选中的任务标记为质检不通过吗？")) return;
    setSubmitting(true);
    try {
      const items = Array.from(selectedIds).map((id) => ({
        task_id: id,
        result: "fail",
        comment: "抽检批次快捷质检不通过",
      }));
      const res = await api.post<BatchInspectionResult>("/inspections/batch/submit", {
        items,
      });
      showToast("success", `批量提交成功：不通过 ${res.data.success_count} 条`);
      setSelectedIds(new Set());
      setShowBatchMenu(false);
      fetchData();
    } catch (e: any) {
      showToast("error", e?.response?.data?.detail || "批量提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickPassAllPending = async () => {
    const pendingIds = pendingTasks.map((t) => t.id);
    if (pendingIds.length === 0) {
      showToast("error", "没有待质检的任务");
      return;
    }
    if (!confirm(`确定将全部 ${pendingIds.length} 条待质检任务标记为通过吗？`)) return;
    setSubmitting(true);
    try {
      const res = await api.post<BatchInspectionResult>("/inspections/batch/quick-pass", {
        task_ids: pendingIds,
        comment: "抽检批次一键全部通过",
      });
      showToast("success", `一键通过成功：${res.data.success_count} 条`);
      setSelectedIds(new Set());
      fetchData();
    } catch (e: any) {
      showToast("error", e?.response?.data?.detail || "操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-sm text-slate-500">加载中...</div>;
  if (!batch) return <div className="text-sm text-slate-500">批次不存在</div>;

  return (
    <div className="space-y-5">
      {toast && (
        <div
          className={cn(
            "fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium",
            toast.type === "success"
              ? "bg-emerald-600 text-white"
              : "bg-red-600 text-white"
          )}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button className="btn btn-secondary" onClick={() => router.back()}>
          <ArrowLeft size={16} />
          返回
        </button>
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-slate-900">{batch.name}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            抽样批次详情 · 创建于 {formatDate(batch.created_at)}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchData}
          disabled={submitting}
        >
          <RefreshCw size={16} className={submitting ? "animate-spin" : ""} />
          刷新
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatBox
            icon={<FlaskConical size={18} />}
            tone="blue"
            label="抽样数量"
            value={stats.total_tasks}
          />
          <StatBox
            icon={<Users size={18} />}
            tone="purple"
            label="已质检完成"
            value={`${stats.inspected_count} / ${stats.total_tasks}`}
          />
          <StatBox
            icon={<CheckCircle2 size={18} />}
            tone="emerald"
            label="质检通过率"
            value={formatPercent(stats.pass_rate)}
            sub={`通过 ${stats.pass_count + stats.arbitrated_count} 条`}
          />
          <StatBox
            icon={<AlertTriangle size={18} />}
            tone="red"
            label="误判率"
            value={formatPercent(stats.misjudgment_rate)}
            sub={`不通过 ${stats.fail_count} 条`}
            highlight={stats.misjudgment_rate > 0.1}
          />
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          <MiniStat label="一致" value={stats.consistent_count} tone="emerald" />
          <MiniStat label="部分一致" value={stats.partial_count} tone="amber" />
          <MiniStat label="不一致" value={stats.inconsistent_count} tone="red" />
          <MiniStat label="待质检" value={stats.pending_count} tone="slate" />
          <MiniStat label="通过" value={stats.pass_count} tone="emerald" />
          <MiniStat label="仲裁" value={stats.arbitrated_count} tone="blue" />
        </div>
      )}

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">批次信息</h3>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <dt className="text-slate-500 text-xs mb-1">抽样策略</dt>
            <dd className="text-slate-800 font-medium">
              {STRATEGY_LABEL[batch.strategy] || batch.strategy}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 text-xs mb-1">抽样方式</dt>
            <dd className="text-slate-800 font-medium">
              {batch.sample_ratio ? (
                <span className="inline-flex items-center gap-1">
                  按比例
                  <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                    {(batch.sample_ratio * 100).toFixed(0)}%
                  </span>
                </span>
              ) : (
                "固定数量"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 text-xs mb-1">一致性筛选</dt>
            <dd className="text-slate-800 font-medium">
              {batch.consistency_filter || "全部"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 text-xs mb-1">创建人</dt>
            <dd className="text-slate-800 font-medium">{batch.created_by}</dd>
          </div>
          <div>
            <dt className="text-slate-500 text-xs mb-1">创建时间</dt>
            <dd className="text-slate-800 font-medium">
              {formatDate(batch.created_at)}
            </dd>
          </div>
          {batch.description && (
            <div className="col-span-2 md:col-span-4">
              <dt className="text-slate-500 text-xs mb-1">批次说明</dt>
              <dd className="text-slate-800">{batch.description}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">
              抽样任务列表（{tasks.length}）
            </h3>
            <div className="flex items-center gap-2">
              {someSelected && (
                <span className="text-xs text-slate-500">
                  已选 <span className="font-semibold text-primary-600">{selectedIds.size}</span> 条
                </span>
              )}

              <div className="relative">
                <button
                  className="btn btn-primary gap-1.5"
                  onClick={() => setShowBatchMenu(!showBatchMenu)}
                  disabled={submitting}
                >
                  <Zap size={14} />
                  快捷操作
                  <ChevronDown size={14} />
                </button>
                {showBatchMenu && (
                  <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-10 overflow-hidden">
                    <button
                      className="w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50 flex items-center gap-2 text-emerald-600"
                      onClick={handleBatchQuickPass}
                      disabled={selectedIds.size === 0 || submitting}
                    >
                      <CheckCircle2 size={16} />
                      选中批量通过
                    </button>
                    <button
                      className="w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50 flex items-center gap-2 text-red-600"
                      onClick={handleBatchQuickFail}
                      disabled={selectedIds.size === 0 || submitting}
                    >
                      <XCircle size={16} />
                      选中批量不通过
                    </button>
                    <div className="border-t border-slate-100" />
                    <button
                      className="w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50 flex items-center gap-2 text-primary-600"
                      onClick={handleQuickPassAllPending}
                      disabled={pendingTasks.length === 0 || submitting}
                    >
                      <Zap size={16} />
                      一键全部通过
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <button
              className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-800"
              onClick={toggleSelectAll}
            >
              {allSelected ? (
                <CheckSquare size={16} className="text-primary-600" />
              ) : (
                <Square size={16} />
              )}
              <span>全选待质检</span>
            </button>
            <span className="text-xs text-slate-400">
              待质检 {pendingTasks.length} 条
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500">
                <th className="px-3 py-3 w-10"></th>
                <th className="px-3 py-3 font-medium">标题 / 编号</th>
                <th className="px-3 py-3 font-medium">任务状态</th>
                <th className="px-3 py-3 font-medium">一致性</th>
                <th className="px-3 py-3 font-medium">标注员</th>
                <th className="px-3 py-3 font-medium">质检结果</th>
                <th className="px-3 py-3 font-medium">更新时间</th>
                <th className="px-3 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length > 0 ? (
                tasks.map((t) => {
                  const isInspected = t.inspection_result && t.inspection_result !== "pending";
                  const isSelected = selectedIds.has(t.id);
                  return (
                    <tr
                      key={t.id}
                      className={cn(
                        "border-b border-slate-100 last:border-0 hover:bg-slate-50/60",
                        isSelected && "bg-primary-50/50"
                      )}
                    >
                      <td className="px-3 py-3.5">
                        {!isInspected ? (
                          <button
                            onClick={() => toggleSelect(t.id)}
                            className="text-slate-400 hover:text-primary-600"
                          >
                            {isSelected ? (
                              <CheckSquare size={18} className="text-primary-600" />
                            ) : (
                              <Square size={18} />
                            )}
                          </button>
                        ) : (
                          <span className="text-slate-300">
                            <CheckSquare size={18} />
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3.5">
                        <div className="font-medium text-slate-800">{t.title}</div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {t.content_id}
                        </div>
                      </td>
                      <td className="px-3 py-3.5">
                        <StatusBadge status={t.status} type="task" />
                      </td>
                      <td className="px-3 py-3.5">
                        <div className="flex flex-col gap-1">
                          <StatusBadge
                            status={t.consistency_status}
                            type="consistency"
                          />
                          {t.consistency_score !== null && (
                            <span className="text-xs text-slate-500">
                              {formatPercent(t.consistency_score)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3.5 text-slate-600 text-xs">
                        {t.annotator_a_name}
                        <span className="text-slate-400"> vs </span>
                        {t.annotator_b_name}
                      </td>
                      <td className="px-3 py-3.5">
                        <StatusBadge status={t.inspection_result} type="inspection" />
                      </td>
                      <td className="px-3 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                        {formatDate(t.updated_at)}
                      </td>
                      <td className="px-3 py-3.5 text-right">
                        {!isInspected ? (
                          <Link
                            href={`/workbench/${t.id}`}
                            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                          >
                            质检
                          </Link>
                        ) : (
                          <Link
                            href={`/workbench/${t.id}`}
                            className="text-slate-500 hover:text-slate-700 text-sm"
                          >
                            查看
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-12 text-center text-slate-500"
                  >
                    暂无抽样任务
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatBox({
  icon,
  tone,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ReactNode;
  tone: "blue" | "emerald" | "amber" | "red" | "purple";
  label: string;
  value: string | number;
  sub?: string;
  highlight?: boolean;
}) {
  const tones: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
    purple: "bg-purple-50 text-purple-600",
  };
  return (
    <div className={cn("card p-5", highlight && "ring-2 ring-red-200")}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-500">{label}</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {value}
          </div>
          {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
        </div>
        <div className={`p-2.5 rounded-lg ${tones[tone]}`}>{icon}</div>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "emerald" | "amber" | "red" | "slate" | "blue";
}) {
  const tones: Record<string, string> = {
    emerald: "text-emerald-600 bg-emerald-50",
    amber: "text-amber-600 bg-amber-50",
    red: "text-red-600 bg-red-50",
    slate: "text-slate-600 bg-slate-100",
    blue: "text-blue-600 bg-blue-50",
  };
  return (
    <div className="card p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div
        className={cn(
          "mt-1 text-lg font-semibold inline-block px-2 py-0.5 rounded",
          tones[tone]
        )}
      >
        {value}
      </div>
    </div>
  );
}
