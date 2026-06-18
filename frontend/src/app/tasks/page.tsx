"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import api from "@/lib/api";
import type { TaskListResponse, TaskListItem, TaskStatus, ConsistencyStatus, InspectionResult } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate, formatPercent } from "@/lib/utils";
import { Search, ChevronLeft, ChevronRight, Filter } from "lucide-react";

export default function TasksPage() {
  const [data, setData] = useState<TaskListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [consistency, setConsistency] = useState<ConsistencyStatus | "">("");
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const fetchData = useCallback(() => {
    setLoading(true);
    setData(null);
    const params: Record<string, any> = { page, page_size: pageSize };
    if (status) params.status = status;
    if (consistency) params.consistency = consistency;
    if (keyword) params.keyword = keyword;
    api
      .get<TaskListResponse>("/tasks", { params })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [page, pageSize, status, consistency, keyword]);

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

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">标注任务列表</h2>
        <p className="text-sm text-slate-500 mt-1">
          查看所有双标注任务，支持按状态、一致性筛选与搜索
        </p>
      </div>

      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-slate-400" />
            <span className="text-sm text-slate-600">筛选：</span>
          </div>
          <select
            className="select w-auto"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as TaskStatus | "");
              setPage(1);
            }}
          >
            <option value="">全部状态</option>
            <option value="pending">待标注</option>
            <option value="double_annotating">双标注中</option>
            <option value="waiting_inspection">待质检</option>
            <option value="inspecting">质检中</option>
            <option value="completed">已完成</option>
          </select>
          <select
            className="select w-auto"
            value={consistency}
            onChange={(e) => {
              setConsistency(e.target.value as ConsistencyStatus | "");
              setPage(1);
            }}
          >
            <option value="">全部一致性</option>
            <option value="consistent">一致</option>
            <option value="partial">部分一致</option>
            <option value="inconsistent">不一致</option>
          </select>
          <div className="relative flex-1 min-w-[240px] max-w-sm">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="text"
              className="input pl-9"
              placeholder="搜索标题/内容/编号"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setKeyword(searchInput);
                  setPage(1);
                }
              }}
            />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-500">
                <th className="px-5 py-3 font-medium">ID / 标题</th>
                <th className="px-5 py-3 font-medium">类型</th>
                <th className="px-5 py-3 font-medium">任务状态</th>
                <th className="px-5 py-3 font-medium">一致性</th>
                <th className="px-5 py-3 font-medium">标注员</th>
                <th className="px-5 py-3 font-medium">质检结果</th>
                <th className="px-5 py-3 font-medium">更新时间</th>
                <th className="px-5 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-5 py-12 text-center text-slate-500">
                    加载中...
                  </td>
                </tr>
              ) : data && data.items.length > 0 ? (
                data.items.map((t) => <TaskRow key={t.id} task={t} />)
              ) : (
                <tr>
                  <td colSpan={8} className="px-5 py-12 text-center text-slate-500">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-200 text-sm">
            <div className="text-slate-500">
              共 {data.total} 条，第 {page} / {totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <button
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft size={16} />
                上一页
              </button>
              <button
                className="btn btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                下一页
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TaskRow({ task }: { task: TaskListItem }) {
  return (
    <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
      <td className="px-5 py-3.5">
        <div className="font-medium text-slate-800">{task.title}</div>
        <div className="text-xs text-slate-500 mt-0.5">{task.content_id}</div>
      </td>
      <td className="px-5 py-3.5 text-slate-600">{task.content_type}</td>
      <td className="px-5 py-3.5">
        <StatusBadge status={task.status} type="task" />
      </td>
      <td className="px-5 py-3.5">
        <div className="flex flex-col gap-1">
          <StatusBadge status={task.consistency_status} type="consistency" />
          {task.consistency_score !== null && (
            <span className="text-xs text-slate-500">
              得分 {formatPercent(task.consistency_score)}
            </span>
          )}
        </div>
      </td>
      <td className="px-5 py-3.5 text-slate-600">
        {task.annotator_a_name && task.annotator_b_name ? (
          <div className="text-xs">
            <div>{task.annotator_a_name}</div>
            <div className="text-slate-400">vs</div>
            <div>{task.annotator_b_name}</div>
          </div>
        ) : (
          <span className="text-slate-400">-</span>
        )}
      </td>
      <td className="px-5 py-3.5">
        <StatusBadge status={task.inspection_result} type="inspection" />
      </td>
      <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">
        {formatDate(task.updated_at)}
      </td>
      <td className="px-5 py-3.5 text-right">
        <Link
          href={`/workbench/${task.id}`}
          className="text-primary-600 hover:text-primary-700 text-sm font-medium"
        >
          查看 / 质检
        </Link>
      </td>
    </tr>
  );
}
