"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { TaskListItem } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatPercent } from "@/lib/utils";
import { SearchCheck, AlertTriangle, CheckCircle2, Clock } from "lucide-react";

const INSPECTOR_ID = 1;
const INSPECTOR_NAME = "质检员-孙丽";

export default function WorkbenchPage() {
  const router = useRouter();
  const [pending, setPending] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [claimingTaskId, setClaimingTaskId] = useState<number | null>(null);

  useEffect(() => {
    api
      .get<TaskListItem[]>("/inspections/pending", { params: { inspector_id: INSPECTOR_ID } })
      .then((r) => setPending(r.data))
      .finally(() => setLoading(false));
  }, []);

  const handleStartInspection = async (taskId: number, e: React.MouseEvent) => {
    e.preventDefault();
    setClaimingTaskId(taskId);
    try {
      const res = await api.post(`/inspections/${taskId}/claim`, {
        inspector_id: INSPECTOR_ID,
        inspector_name: INSPECTOR_NAME,
      });
      if (res.data.claimed) {
        router.push(`/workbench/${taskId}`);
      } else {
        alert(res.data.message || "该任务已被他人领取，请选择其他任务");
        setPending((prev) => prev.filter((t) => t.id !== taskId));
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || "领取任务失败，请重试");
    } finally {
      setClaimingTaskId(null);
    }
  };

  const inconsistent = pending.filter(
    (t) => t.consistency_status === "inconsistent"
  );
  const partial = pending.filter((t) => t.consistency_status === "partial");
  const consistent = pending.filter(
    (t) => t.consistency_status === "consistent"
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">质检工作台</h2>
        <p className="text-sm text-slate-500 mt-1">
          处理待质检的双标注任务，对比标注结果并进行仲裁
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5 border-l-4 border-l-red-500">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm text-slate-500">不一致待处理</div>
              <div className="mt-1 text-3xl font-semibold text-red-600">
                {inconsistent.length}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-red-50 text-red-500">
              <AlertTriangle size={22} />
            </div>
          </div>
        </div>
        <div className="card p-5 border-l-4 border-l-amber-500">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm text-slate-500">部分一致待复核</div>
              <div className="mt-1 text-3xl font-semibold text-amber-600">
                {partial.length}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-amber-50 text-amber-500">
              <Clock size={22} />
            </div>
          </div>
        </div>
        <div className="card p-5 border-l-4 border-l-emerald-500">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm text-slate-500">一致待确认</div>
              <div className="mt-1 text-3xl font-semibold text-emerald-600">
                {consistent.length}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-500">
              <CheckCircle2 size={22} />
            </div>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2">
            <SearchCheck size={18} className="text-primary-600" />
            待质检任务列表（{pending.length}）
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500">
                <th className="px-5 py-3 font-medium">标题 / 编号</th>
                <th className="px-5 py-3 font-medium">一致性</th>
                <th className="px-5 py-3 font-medium">标注员 A vs B</th>
                <th className="px-5 py-3 font-medium">更新时间</th>
                <th className="px-5 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                    加载中...
                  </td>
                </tr>
              ) : pending.length > 0 ? (
                pending.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60"
                  >
                    <td className="px-5 py-3.5">
                      <div className="font-medium text-slate-800">{t.title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {t.content_id}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
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
                    <td className="px-5 py-3.5 text-slate-600 text-xs">
                      {t.annotator_a_name}
                      <span className="text-slate-400"> vs </span>
                      {t.annotator_b_name}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                      {formatDate(t.updated_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        className="btn btn-primary"
                        onClick={(e) => handleStartInspection(t.id, e)}
                        disabled={claimingTaskId === t.id}
                      >
                        {claimingTaskId === t.id ? "领取中..." : "开始质检"}
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                    🎉 当前没有待质检任务，做得好！
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
