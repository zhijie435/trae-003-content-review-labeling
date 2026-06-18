"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import type {
  AnnotationTaskDetail,
  AnnotationResult,
  InspectionOut,
  InspectionSubmit,
} from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  formatDate,
  formatPercent,
  CONSISTENCY_LABEL,
} from "@/lib/utils";
import {
  ArrowLeft,
  Check,
  X,
  Scale,
  User,
  MessageSquare,
  AlertCircle,
  Award,
} from "lucide-react";
import { cn } from "@/lib/utils";

const LABEL_OPTIONS: Record<string, string[]> = {
  risk_level: ["低风险", "中风险", "高风险"],
  category: ["合规", "夸大宣传", "辱骂攻击", "引流广告", "敏感信息", "其他违规"],
  suggestion: ["通过", "警告", "驳回", "封禁"],
};

const LABEL_LABELS: Record<string, string> = {
  risk_level: "风险等级",
  category: "违规分类",
  suggestion: "处理建议",
};

const INSPECTOR_ID = 1;
const INSPECTOR_NAME = "质检员-孙丽";

export default function InspectionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const taskId = parseInt(params.id as string);

  const [task, setTask] = useState<AnnotationTaskDetail | null>(null);
  const [inspections, setInspections] = useState<InspectionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [claimed, setClaimed] = useState(false);

  const [result, setResult] = useState<InspectionSubmit["result"]>("pending");
  const [comment, setComment] = useState("");
  const [score, setScore] = useState<number | "">("");
  const [finalAnnotation, setFinalAnnotation] = useState<AnnotationResult>({
    risk_level: "",
    category: "",
    suggestion: "",
  });
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const releaseTask = useCallback(async () => {
    if (!taskId || !claimed) return;
    try {
      await api.post(`/inspections/${taskId}/release`, {
        inspector_id: INSPECTOR_ID,
      });
    } catch (e) {
      console.error("Failed to release task:", e);
    }
  }, [taskId, claimed]);

  useEffect(() => {
    if (!taskId) return;

    const initTask = async () => {
      try {
        const [t, insp] = await Promise.all([
          api.get<AnnotationTaskDetail>(`/tasks/${taskId}`),
          api.get<InspectionOut[]>(`/tasks/${taskId}/inspections`),
        ]);
        setTask(t.data);
        setInspections(insp.data);
        if (t.data.annotations) {
          const ann = t.data.annotations;
          setFinalAnnotation({
            risk_level: ann.result_a.risk_level,
            category: ann.result_a.category,
            suggestion: ann.result_a.suggestion,
          });
        }

        if (!t.data.claimed_by || t.data.claimed_by !== INSPECTOR_ID) {
          const claimRes = await api.post(`/inspections/${taskId}/claim`, {
            inspector_id: INSPECTOR_ID,
            inspector_name: INSPECTOR_NAME,
          });
          if (!claimRes.data.claimed) {
            setToast({ type: "error", msg: claimRes.data.message || "该任务已被他人领取" });
            setTimeout(() => router.push("/workbench"), 1500);
            return;
          }
        }
        setClaimed(true);
      } finally {
        setLoading(false);
      }
    };

    initTask();

    const handleBeforeUnload = () => {
      if (claimed && !submitting) {
        navigator.sendBeacon(
          `/api/inspections/${taskId}/release`,
          JSON.stringify({ inspector_id: INSPECTOR_ID })
        );
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      if (claimed && !submitting) {
        releaseTask();
      }
    };
  }, [taskId, router, claimed, submitting, releaseTask]);

  const submitWithResult = useCallback(async (submitResult: InspectionSubmit["result"]) => {
    if (!taskId) return;
    if (submitResult === "pending") {
      setToast({ type: "error", msg: "请选择质检结果" });
      return;
    }
    const payload: InspectionSubmit = {
      result: submitResult,
      comment: comment || undefined,
      score: score === "" ? undefined : Number(score),
    };
    if (submitResult === "arbitrated") {
      if (!finalAnnotation.risk_level || !finalAnnotation.category || !finalAnnotation.suggestion) {
        setToast({ type: "error", msg: "仲裁时需要填写完整的最终标注结果" });
        return;
      }
      payload.final_annotation = finalAnnotation;
    }

    setSubmitting(true);
    try {
      await api.post<InspectionOut>(`/inspections/${taskId}`, payload, {
        params: {
          inspector_id: INSPECTOR_ID,
          inspector_name: INSPECTOR_NAME,
        },
      });
      setClaimed(false);
      setToast({ type: "success", msg: "质检提交成功" });
      setTimeout(() => router.push("/workbench"), 800);
    } catch (e: any) {
      setToast({
        type: "error",
        msg: e?.response?.data?.detail || "提交失败",
      });
    } finally {
      setSubmitting(false);
      setTimeout(() => setToast(null), 3000);
    }
  }, [taskId, comment, score, finalAnnotation, router]);

  const handleSubmit = useCallback(() => {
    submitWithResult(result);
  }, [submitWithResult, result]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }
      if (submitting) return;

      if (e.key === "1") {
        setResult("pass");
        submitWithResult("pass");
      } else if (e.key === "2") {
        setResult("arbitrated");
      } else if (e.key === "3") {
        setResult("fail");
        submitWithResult("fail");
      } else if (e.key === "Enter") {
        if (result !== "pending") {
          submitWithResult(result);
        }
      } else if (e.key === "Escape") {
        router.back();
      }
    },
    [result, submitting, router, submitWithResult]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (loading) return <div className="text-sm text-slate-500">加载中...</div>;
  if (!task) return <div className="text-sm text-slate-500">任务不存在</div>;

  const ann = task.annotations;
  const diff = ann?.diff_detail || {};
  const diffKeys = Object.keys(diff);

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
        <button
          className="btn btn-secondary"
          onClick={() => router.back()}
        >
          <ArrowLeft size={16} />
          返回
        </button>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{task.title}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {task.content_id} · {task.content_type}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <StatusBadge status={task.status} type="task" />
          {ann && (
            <StatusBadge status={ann.consistency_status} type="consistency" />
          )}
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">待审核内容</h3>
        <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
          <p className="text-slate-800 leading-relaxed whitespace-pre-wrap">
            {task.content}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
          <span>创建时间：{formatDate(task.created_at)}</span>
          <span>更新时间：{formatDate(task.updated_at)}</span>
        </div>
      </div>

      {ann && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <AnnotatorPanel
            title="标注员 A"
            annotator={ann.annotator_a?.name}
            time={ann.annotated_at_a}
            result={ann.result_a}
            diff={diff}
            side="a"
          />
          <AnnotatorPanel
            title="标注员 B"
            annotator={ann.annotator_b?.name}
            time={ann.annotated_at_b}
            result={ann.result_b}
            diff={diff}
            side="b"
          />
        </div>
      )}

      {ann && diffKeys.length > 0 && (
        <div className="card p-5 border-l-4 border-l-amber-400">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <AlertCircle size={16} className="text-amber-500" />
            不一致字段对比（{diffKeys.length} 处）
          </h3>
          <div className="space-y-3">
            {diffKeys.map((k) => (
              <div
                key={k}
                className="grid grid-cols-[120px_1fr_1fr] gap-4 items-center bg-slate-50 rounded-lg p-3"
              >
                <div className="text-sm font-medium text-slate-600">
                  {LABEL_LABELS[k] || k}
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">标注员 A</div>
                  <div className="text-sm font-medium text-red-600 bg-red-50 inline-block px-2.5 py-1 rounded">
                    {diff[k].a}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">标注员 B</div>
                  <div className="text-sm font-medium text-blue-600 bg-blue-50 inline-block px-2.5 py-1 rounded">
                    {diff[k].b}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {ann && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Scale size={16} className="text-primary-600" />
              一致性分析
            </h3>
            <span className="text-sm font-semibold text-slate-800">
              {CONSISTENCY_LABEL[ann.consistency_status]} ·{" "}
              {formatPercent(ann.consistency_score)}
            </span>
          </div>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full",
                (ann.consistency_score ?? 0) >= 0.8
                  ? "bg-emerald-500"
                  : (ann.consistency_score ?? 0) >= 0.5
                  ? "bg-amber-500"
                  : "bg-red-500"
              )}
              style={{ width: `${(ann.consistency_score ?? 0) * 100}%` }}
            />
          </div>
        </div>
      )}

      {inspections.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">历史质检记录</h3>
          <div className="space-y-3">
            {inspections.map((i) => (
              <div
                key={i.id}
                className="border border-slate-200 rounded-lg p-4 bg-slate-50/50"
              >
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-sm font-medium text-slate-700">
                    {i.inspector_name}
                  </span>
                  <StatusBadge status={i.result} type="inspection" />
                  {i.score !== null && (
                    <span className="text-xs text-slate-500">
                      评分：{i.score} 分
                    </span>
                  )}
                  <span className="ml-auto text-xs text-slate-400">
                    {formatDate(i.created_at)}
                  </span>
                </div>
                {i.comment && (
                  <p className="text-sm text-slate-600 flex items-start gap-2">
                    <MessageSquare size={14} className="mt-0.5 text-slate-400" />
                    {i.comment}
                  </p>
                )}
                {i.final_annotation && (
                  <div className="mt-3 pt-3 border-t border-slate-200">
                    <div className="text-xs text-slate-500 mb-2">仲裁最终标注：</div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(i.final_annotation).map(([k, v]) => (
                        <span
                          key={k}
                          className="px-2.5 py-1 bg-primary-50 text-primary-700 rounded text-xs font-medium"
                        >
                          {LABEL_LABELS[k] || k}：{v}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <Award size={16} className="text-primary-600" />
          提交质检结果
        </h3>

        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-slate-700">
                质检结论 *
              </label>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-600 font-mono">1</kbd>
                <span>通过</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-600 font-mono">2</kbd>
                <span>仲裁</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-600 font-mono">3</kbd>
                <span>不通过</span>
                <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-slate-600 font-mono">Enter</kbd>
                <span>提交</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <ResultOption
                active={result === "pass"}
                onClick={() => setResult("pass")}
                color="emerald"
                icon={<Check size={16} />}
                label="通过"
                desc="双标注一致且结果正确"
                shortcut="1"
              />
              <ResultOption
                active={result === "arbitrated"}
                onClick={() => setResult("arbitrated")}
                color="blue"
                icon={<Scale size={16} />}
                label="仲裁"
                desc="标注结果分歧，给出最终结论"
                shortcut="2"
              />
              <ResultOption
                active={result === "fail"}
                onClick={() => setResult("fail")}
                color="red"
                icon={<X size={16} />}
                label="不通过"
                desc="标注错误，需重新标注"
                shortcut="3"
              />
            </div>
          </div>

          {result === "arbitrated" && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="text-sm font-semibold text-blue-800 mb-3">
                请填写仲裁后的最终标注结果
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.keys(LABEL_OPTIONS).map((k) => (
                  <div key={k}>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">
                      {LABEL_LABELS[k]}
                    </label>
                    <select
                      className="select"
                      value={(finalAnnotation as any)[k] || ""}
                      onChange={(e) =>
                        setFinalAnnotation({
                          ...finalAnnotation,
                          [k]: e.target.value,
                        })
                      }
                    >
                      <option value="">请选择</option>
                      {LABEL_OPTIONS[k].map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                质检备注
              </label>
              <textarea
                className="input min-h-[90px] resize-y"
                placeholder="请输入质检说明或反馈..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                质量评分（0-100）
              </label>
              <input
                type="number"
                min={0}
                max={100}
                className="input"
                placeholder="例如：85"
                value={score}
                onChange={(e) =>
                  setScore(e.target.value === "" ? "" : parseInt(e.target.value))
                }
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button className="btn btn-secondary" onClick={() => router.back()}>
              取消
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? "提交中..." : "提交质检结果"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AnnotatorPanel({
  title,
  annotator,
  time,
  result,
  diff,
  side,
}: {
  title: string;
  annotator?: string | null;
  time?: string | null;
  result: AnnotationResult;
  diff: Record<string, { a: string; b: string }>;
  side: "a" | "b";
}) {
  const sideColor =
    side === "a"
      ? "border-l-red-400 bg-red-50/30"
      : "border-l-blue-400 bg-blue-50/30";
  return (
    <div className={cn("card p-5 border-l-4", sideColor)}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold",
              side === "a" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"
            )}
          >
            <User size={16} />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-800">{title}</div>
            <div className="text-xs text-slate-500">{annotator || "未分配"}</div>
          </div>
        </div>
        {time && (
          <div className="text-xs text-slate-400 whitespace-nowrap">
            标注于 {formatDate(time)}
          </div>
        )}
      </div>
      <div className="space-y-3">
        {Object.entries(result).map(([k, v]) => {
          const hasDiff = !!diff[k];
          return (
            <div
              key={k}
              className={cn(
                "flex items-center justify-between px-3 py-2.5 rounded-lg border",
                hasDiff
                  ? "bg-amber-50 border-amber-200"
                  : "bg-white border-slate-200"
              )}
            >
              <span className="text-sm text-slate-600">
                {LABEL_LABELS[k] || k}
              </span>
              <span
                className={cn(
                  "text-sm font-medium px-2.5 py-0.5 rounded",
                  hasDiff
                    ? side === "a"
                      ? "bg-red-100 text-red-700"
                      : "bg-blue-100 text-blue-700"
                    : "bg-slate-100 text-slate-700"
                )}
              >
                {v}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResultOption({
  active,
  onClick,
  color,
  icon,
  label,
  desc,
  shortcut,
}: {
  active: boolean;
  onClick: () => void;
  color: "emerald" | "blue" | "red";
  icon: React.ReactNode;
  label: string;
  desc: string;
  shortcut?: string;
}) {
  const colors: Record<string, string> = {
    emerald: active
      ? "bg-emerald-50 border-emerald-500 ring-2 ring-emerald-200"
      : "bg-white border-slate-300 hover:border-emerald-300",
    blue: active
      ? "bg-blue-50 border-blue-500 ring-2 ring-blue-200"
      : "bg-white border-slate-300 hover:border-blue-300",
    red: active
      ? "bg-red-50 border-red-500 ring-2 ring-red-200"
      : "bg-white border-slate-300 hover:border-red-300",
  };
  const iconColors: Record<string, string> = {
    emerald: active ? "text-emerald-600" : "text-slate-400",
    blue: active ? "text-blue-600" : "text-slate-400",
    red: active ? "text-red-600" : "text-slate-400",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex-1 min-w-[180px] text-left p-4 rounded-xl border-2 transition-all relative",
        colors[color]
      )}
    >
      {shortcut && (
        <kbd className="absolute top-3 right-3 px-1.5 py-0.5 bg-white/80 border border-slate-200 rounded text-[10px] font-mono text-slate-500">
          {shortcut}
        </kbd>
      )}
      <div className="flex items-center gap-2">
        <div className={iconColors[color]}>{icon}</div>
        <span
          className={cn(
            "font-semibold",
            active
              ? color === "emerald"
                ? "text-emerald-700"
                : color === "blue"
                ? "text-blue-700"
                : "text-red-700"
              : "text-slate-700"
          )}
        >
          {label}
        </span>
      </div>
      <p className="text-xs text-slate-500 mt-1.5">{desc}</p>
    </button>
  );
}
