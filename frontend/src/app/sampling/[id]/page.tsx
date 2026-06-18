"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import type { SamplingBatchOut, TaskListItem } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatPercent } from "@/lib/utils";
import { ArrowLeft, FlaskConical, Users, CheckCircle2 } from "lucide-react";

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!batchId) return;
    Promise.all([
      api.get<SamplingBatchOut>(`/sampling/batches/${batchId}`),
      api.get<TaskListItem[]>(`/sampling/batches/${batchId}/tasks`),
    ])
      .then(([b, t]) => {
        setBatch(b.data);
        setTasks(t.data);
      })
      .finally(() => setLoading(false));
  }, [batchId]);

  if (loading) return <div className="text-sm text-slate-500">加载中...</div>;
  if (!batch) return <div className="text-sm text-slate-500">批次不存在</div>;

  const inspected = tasks.filter(
    (t) => t.status === "completed" || t.inspection_result
  ).length;
  const inconsistent = tasks.filter(
    (t) => t.consistency_status === "inconsistent"
  ).length;
  const consistent = tasks.filter(
    (t) => t.consistency_status === "consistent"
  ).length;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button className="btn btn-secondary" onClick={() => router.back()}>
          <ArrowLeft size={16} />
          返回
        </button>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{batch.name}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            抽样批次详情 · 创建于 {formatDate(batch.created_at)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatBox
          icon={<FlaskConical size={18} />}
          tone="blue"
          label="抽样数量"
          value={batch.sample_count}
        />
        <StatBox
          icon={<Users size={18} />}
          tone="purple"
          label="已质检完成"
          value={`${inspected} / ${tasks.length}`}
        />
        <StatBox
          icon={<CheckCircle2 size={18} />}
          tone="emerald"
          label="一致数量"
          value={consistent}
        />
        <StatBox
          icon={<CheckCircle2 size={18} />}
          tone="red"
          label="不一致数量"
          value={inconsistent}
        />
      </div>

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
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">
            抽样任务列表（{tasks.length}）
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500">
                <th className="px-5 py-3 font-medium">标题 / 编号</th>
                <th className="px-5 py-3 font-medium">任务状态</th>
                <th className="px-5 py-3 font-medium">一致性</th>
                <th className="px-5 py-3 font-medium">标注员</th>
                <th className="px-5 py-3 font-medium">质检结果</th>
                <th className="px-5 py-3 font-medium">更新时间</th>
                <th className="px-5 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length > 0 ? (
                tasks.map((t) => (
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
                      <StatusBadge status={t.status} type="task" />
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
                    <td className="px-5 py-3.5">
                      <StatusBadge status={t.inspection_result} type="inspection" />
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                      {formatDate(t.updated_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        href={`/workbench/${t.id}`}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        质检
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={7}
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
}: {
  icon: React.ReactNode;
  tone: "blue" | "emerald" | "amber" | "red" | "purple";
  label: string;
  value: string | number;
}) {
  const tones: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
    purple: "bg-purple-50 text-purple-600",
  };
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-500">{label}</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {value}
          </div>
        </div>
        <div className={`p-2.5 rounded-lg ${tones[tone]}`}>{icon}</div>
      </div>
    </div>
  );
}
