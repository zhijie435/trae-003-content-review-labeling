"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import type { StatisticsOut } from "@/lib/types";
import { formatPercent } from "@/lib/utils";
import {
  ClipboardList,
  Users,
  CheckCircle2,
  XCircle,
  Scale,
  AlertCircle,
  TrendingUp,
  FlaskConical,
} from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  tone?: "blue" | "emerald" | "amber" | "red" | "purple";
  sub?: string;
}

function StatCard({ title, value, icon, tone = "blue", sub }: StatCardProps) {
  const tones: Record<string, string> = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
    red: "bg-red-50 text-red-600",
    purple: "bg-purple-50 text-purple-600",
  };
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-slate-500">{title}</div>
          <div className="mt-2 text-2xl font-semibold text-slate-900">
            {value}
          </div>
          {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
        </div>
        <div className={`p-2.5 rounded-lg ${tones[tone]}`}>{icon}</div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<StatisticsOut | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(() => {
    setLoading(true);
    setStats(null);
    api
      .get<StatisticsOut>("/statistics")
      .then((r) => setStats(r.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        fetchStats();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [fetchStats]);

  if (loading) {
    return <div className="text-sm text-slate-500">加载中...</div>;
  }
  if (!stats) return <div>加载失败</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">数据看板</h2>
          <p className="text-sm text-slate-500 mt-1">
            双标注一致性、质检进度和整体质量概况
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="总任务数"
          value={stats.total_tasks}
          icon={<ClipboardList size={20} />}
          tone="blue"
        />
        <StatCard
          title="双标注完成"
          value={stats.double_annotated}
          icon={<Users size={20} />}
          tone="purple"
          sub={`待质检 ${stats.waiting_inspection} 条`}
        />
        <StatCard
          title="一致性率"
          value={formatPercent(stats.consistency_rate)}
          icon={<Scale size={20} />}
          tone="emerald"
          sub={`一致 ${stats.consistent_count} / 部分 ${stats.partial_count} / 不一致 ${stats.inconsistent_count}`}
        />
        <StatCard
          title="质检通过率"
          value={formatPercent(stats.pass_rate)}
          icon={<TrendingUp size={20} />}
          tone="amber"
          sub={`通过 ${stats.pass_count} / 仲裁 ${stats.arbitrated_count} / 不通过 ${stats.fail_count}`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card p-5 lg:col-span-1">
          <h3 className="font-semibold text-slate-900 mb-4">双标注一致性分布</h3>
          <div className="space-y-4">
            <ProgressRow
              label="一致"
              value={stats.consistent_count}
              total={stats.double_annotated}
              color="bg-emerald-500"
            />
            <ProgressRow
              label="部分一致"
              value={stats.partial_count}
              total={stats.double_annotated}
              color="bg-amber-500"
            />
            <ProgressRow
              label="不一致"
              value={stats.inconsistent_count}
              total={stats.double_annotated}
              color="bg-red-500"
            />
          </div>
        </div>

        <div className="card p-5 lg:col-span-1">
          <h3 className="font-semibold text-slate-900 mb-4">质检结果分布</h3>
          <div className="space-y-4">
            <ProgressRow
              label="通过"
              value={stats.pass_count}
              total={stats.pass_count + stats.arbitrated_count + stats.fail_count}
              color="bg-emerald-500"
            />
            <ProgressRow
              label="仲裁"
              value={stats.arbitrated_count}
              total={stats.pass_count + stats.arbitrated_count + stats.fail_count}
              color="bg-blue-500"
            />
            <ProgressRow
              label="不通过"
              value={stats.fail_count}
              total={stats.pass_count + stats.arbitrated_count + stats.fail_count}
              color="bg-red-500"
            />
          </div>
        </div>

        <div className="card p-5 lg:col-span-1">
          <h3 className="font-semibold text-slate-900 mb-4">抽样批次</h3>
          <div className="flex items-center justify-center py-4">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary-50 text-primary-600 flex items-center justify-center mx-auto">
                <FlaskConical size={28} />
              </div>
              <div className="mt-3 text-3xl font-semibold text-slate-900">
                {stats.total_sampling_batches}
              </div>
              <div className="text-sm text-slate-500 mt-1">累计抽样批次</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 mb-4">标注员一致性排名</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2.5 pr-4 font-medium">标注员</th>
                <th className="py-2.5 pr-4 font-medium">标注总数</th>
                <th className="py-2.5 pr-4 font-medium">一致数量</th>
                <th className="py-2.5 pr-4 font-medium">一致性率</th>
                <th className="py-2.5 font-medium w-48">进度</th>
              </tr>
            </thead>
            <tbody>
              {stats.per_annotator_stats
                .sort((a, b) => b.consistency_rate - a.consistency_rate)
                .map((s) => (
                  <tr key={s.annotator_id} className="border-b border-slate-100 last:border-0">
                    <td className="py-3 pr-4 font-medium text-slate-800">{s.name}</td>
                    <td className="py-3 pr-4 text-slate-600">{s.total_tasks}</td>
                    <td className="py-3 pr-4 text-slate-600">{s.consistent_count}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={
                          s.consistency_rate >= 0.8
                            ? "text-emerald-600 font-medium"
                            : s.consistency_rate >= 0.6
                            ? "text-amber-600 font-medium"
                            : "text-red-600 font-medium"
                        }
                      >
                        {formatPercent(s.consistency_rate)}
                      </span>
                    </td>
                    <td className="py-3">
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            s.consistency_rate >= 0.8
                              ? "bg-emerald-500"
                              : s.consistency_rate >= 0.6
                              ? "bg-amber-500"
                              : "bg-red-500"
                          }`}
                          style={{ width: `${s.consistency_rate * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ProgressRow({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const percent = total > 0 ? (value / total) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="text-slate-700">{label}</span>
        <span className="text-slate-500">
          {value} ({percent.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
