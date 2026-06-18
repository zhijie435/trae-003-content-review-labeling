"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import type {
  SamplingBatchOut,
  SamplingRequest,
  ConsistencyStatus,
} from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { FlaskConical, Plus, ChevronRight, Package, Filter } from "lucide-react";

const STRATEGY_LABEL: Record<string, string> = {
  random: "随机抽样",
  inconsistent_first: "不一致优先",
  high_score_first: "高一致性优先",
};

export default function SamplingPage() {
  const [batches, setBatches] = useState<SamplingBatchOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const [sampleMode, setSampleMode] = useState<"count" | "ratio">("count");
  const [form, setForm] = useState<Partial<SamplingRequest>>({
    name: "",
    description: "",
    sample_count: 10,
    sample_ratio: 0.1,
    strategy: "random",
    consistency_filter: undefined,
    created_by: "质检员-孙丽",
  });
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(
    null
  );

  const fetchBatches = useCallback(() => {
    setLoading(true);
    setBatches([]);
    api
      .get<SamplingBatchOut[]>("/sampling/batches")
      .then((r) => setBatches(r.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchBatches();
  }, [fetchBatches]);

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        fetchBatches();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [fetchBatches]);

  const handleCreate = async () => {
    if (!form.name?.trim()) {
      setToast({ type: "error", msg: "请输入批次名称" });
      return;
    }
    if (sampleMode === "count" && (!form.sample_count || form.sample_count <= 0)) {
      setToast({ type: "error", msg: "请输入有效的抽样数量" });
      return;
    }
    if (sampleMode === "ratio" && (!form.sample_ratio || form.sample_ratio <= 0 || form.sample_ratio > 1)) {
      setToast({ type: "error", msg: "请输入有效的抽样比例（0-1）" });
      return;
    }

    const submitData = { ...form };
    if (sampleMode === "count") {
      delete submitData.sample_ratio;
    } else {
      delete submitData.sample_count;
    }

    setSubmitting(true);
    try {
      await api.post<SamplingBatchOut>("/sampling", submitData);
      setToast({ type: "success", msg: "抽样批次创建成功" });
      setShowModal(false);
      setForm({
        name: "",
        description: "",
        sample_count: 10,
        sample_ratio: 0.1,
        strategy: "random",
        consistency_filter: undefined,
        created_by: "质检员-孙丽",
      });
      fetchBatches();
    } catch (e: any) {
      setToast({
        type: "error",
        msg: e?.response?.data?.detail || "创建失败",
      });
    } finally {
      setSubmitting(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  return (
    <div className="space-y-5">
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === "success"
              ? "bg-emerald-600 text-white"
              : "bg-red-600 text-white"
          }`}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">抽样管理</h2>
          <p className="text-sm text-slate-500 mt-1">
            按策略创建质检抽样批次，用于重点复核双标注结果
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} />
          新建抽样批次
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-500">累计抽样批次</div>
              <div className="mt-1 text-3xl font-semibold text-slate-900">
                {batches.length}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-primary-50 text-primary-600">
              <FlaskConical size={22} />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-500">累计抽样任务</div>
              <div className="mt-1 text-3xl font-semibold text-slate-900">
                {batches.reduce((s, b) => s + b.sample_count, 0)}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600">
              <Package size={22} />
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-500">最新抽样批次</div>
              <div className="mt-1 text-lg font-semibold text-slate-900 truncate">
                {batches[0]?.name || "-"}
              </div>
            </div>
            <div className="p-2.5 rounded-lg bg-amber-50 text-amber-600">
              <Filter size={22} />
            </div>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">抽样批次列表</h3>
        </div>
        {loading ? (
          <div className="px-5 py-12 text-center text-slate-500 text-sm">
            加载中...
          </div>
        ) : batches.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {batches.map((b) => (
              <a
                key={b.id}
                href={`/sampling/${b.id}`}
                className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
                  <FlaskConical size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-800 group-hover:text-primary-600 transition-colors">
                    {b.name}
                  </div>
                  {b.description && (
                    <div className="text-sm text-slate-500 mt-0.5 truncate">
                      {b.description}
                    </div>
                  )}
                  <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>
                      策略：
                      <span className="text-slate-700">
                        {STRATEGY_LABEL[b.strategy] || b.strategy}
                      </span>
                    </span>
                    <span>
                      样本数：
                      <span className="text-slate-700">{b.sample_count}</span>
                    </span>
                    {b.sample_ratio && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                        按比例 {(b.sample_ratio * 100).toFixed(0)}% 生成
                      </span>
                    )}
                    {b.consistency_filter && (
                      <span>
                        一致性筛选：
                        <span className="text-slate-700 capitalize">
                          {b.consistency_filter}
                        </span>
                      </span>
                    )}
                    <span>
                      创建人：
                      <span className="text-slate-700">{b.created_by}</span>
                    </span>
                    <span>{formatDate(b.created_at)}</span>
                  </div>
                </div>
                <ChevronRight
                  size={18}
                  className="text-slate-400 group-hover:text-primary-500 transition-colors shrink-0"
                />
              </a>
            ))}
          </div>
        ) : (
          <div className="px-5 py-12 text-center text-slate-500 text-sm">
            暂无抽样批次，点击右上角按钮创建
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">新建抽样批次</h3>
              <button
                className="text-slate-400 hover:text-slate-600"
                onClick={() => setShowModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  批次名称 *
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="例如：6月第二轮质检抽样"
                  value={form.name || ""}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  批次说明
                </label>
                <textarea
                  className="input min-h-[70px] resize-y"
                  placeholder="简要描述本次抽样的目的和范围"
                  value={form.description || ""}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  抽样方式
                </label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium transition-colors ${
                      sampleMode === "count"
                        ? "border-primary-500 bg-primary-50 text-primary-700"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => setSampleMode("count")}
                  >
                    按固定数量
                  </button>
                  <button
                    type="button"
                    className={`flex-1 py-2 px-4 rounded-lg border text-sm font-medium transition-colors ${
                      sampleMode === "ratio"
                        ? "border-primary-500 bg-primary-50 text-primary-700"
                        : "border-slate-200 text-slate-600 hover:bg-slate-50"
                    }`}
                    onClick={() => setSampleMode("ratio")}
                  >
                    按比例自动
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {sampleMode === "count" ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      抽样数量 *
                    </label>
                    <input
                      type="number"
                      min={1}
                      className="input"
                      value={form.sample_count || 10}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          sample_count: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      抽样比例 *
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        step={0.01}
                        min={0.01}
                        max={1}
                        className="input pr-10"
                        value={form.sample_ratio || 0.1}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            sample_ratio: parseFloat(e.target.value) || 0,
                          })
                        }
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
                        ({((form.sample_ratio || 0.1) * 100).toFixed(0)}%)
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      范围：1% - 100%，系统按符合条件的任务数自动计算
                    </p>
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    抽样策略
                  </label>
                  <select
                    className="select"
                    value={form.strategy || "random"}
                    onChange={(e) =>
                      setForm({ ...form, strategy: e.target.value })
                    }
                  >
                    <option value="random">随机抽样</option>
                    <option value="inconsistent_first">不一致优先</option>
                    <option value="high_score_first">高一致性优先</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  一致性筛选
                </label>
                <select
                  className="select"
                  value={form.consistency_filter || ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      consistency_filter: (e.target.value ||
                        undefined) as ConsistencyStatus | undefined,
                    })
                  }
                >
                  <option value="">不筛选（全部）</option>
                  <option value="consistent">仅一致</option>
                  <option value="partial">仅部分一致</option>
                  <option value="inconsistent">仅不一致</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  创建人
                </label>
                <input
                  type="text"
                  className="input"
                  value={form.created_by || ""}
                  onChange={(e) =>
                    setForm({ ...form, created_by: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
              <button
                className="btn btn-secondary"
                onClick={() => setShowModal(false)}
              >
                取消
              </button>
              <button
                className="btn btn-primary"
                onClick={handleCreate}
                disabled={submitting}
              >
                {submitting ? "创建中..." : "创建抽样批次"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
