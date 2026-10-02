"use client";

import React, { useState } from "react";
import { ResearchTask, ResearchDomain } from "@/lib/types";
import { CheckCircle2, Trash2, Undo2, ShieldCheck, ArrowRight, Search, Loader2 } from "lucide-react";

interface PlanReviewProps {
  companyName: string;
  threadId: string;
  initialPlan: ResearchTask[];
  onApprove: () => void;
  onEdit: (filteredPlan: ResearchTask[]) => void;
  isSubmitting: boolean;
}

const DOMAIN_CONFIG: Record<
  string,
  { label: string; badgeClass: string; borderClass: string }
> = {
  pricing_packaging: {
    label: "Pricing & Packaging",
    badgeClass: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    borderClass: "border-l-amber-500",
  },
  feature_set: {
    label: "Features & Architecture",
    badgeClass: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
    borderClass: "border-l-cyan-500",
  },
  customer_sentiment: {
    label: "Customer Sentiment",
    badgeClass: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    borderClass: "border-l-rose-500",
  },
  news_funding: {
    label: "News & Capitalization",
    badgeClass: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    borderClass: "border-l-emerald-500",
  },
  positioning_messaging: {
    label: "Positioning & ICP",
    badgeClass: "bg-purple-500/15 text-purple-300 border-purple-500/30",
    borderClass: "border-l-purple-500",
  },
};

export function PlanReview({
  companyName,
  threadId,
  initialPlan,
  onApprove,
  onEdit,
  isSubmitting,
}: PlanReviewProps) {
  const [removedTaskIds, setRemovedTaskIds] = useState<Set<string>>(new Set());

  const toggleRemoveTask = (taskId: string) => {
    if (isSubmitting) return;
    setRemovedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const activeTasks = initialPlan.filter((t) => !removedTaskIds.has(t.task_id));
  const isModified = removedTaskIds.size > 0;
  const canSubmit = activeTasks.length > 0 && !isSubmitting;

  const handleSubmit = () => {
    if (!canSubmit) return;
    if (isModified) {
      onEdit(activeTasks);
    } else {
      onApprove();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Checkpoint Banner */}
      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 mb-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                Checkpoint 1
              </span>
              <span className="text-xs text-zinc-400 font-mono">
                Human-in-the-Loop Review
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Research Agenda for <span className="text-amber-400">{companyName}</span>
            </h2>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1 max-w-2xl">
              The Planner agent has proposed {initialPlan.length} research tasks. Review the agenda before launching parallel web search agents. You may prune irrelevant tasks or approve the full plan.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono text-zinc-400 bg-white/[0.03] px-3 py-2 rounded-lg border border-white/[0.06] self-start sm:self-center">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            <span>Plan Intercepted</span>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-4 mb-8">
        <div className="flex items-center justify-between text-xs text-zinc-400 px-1 font-medium">
          <span>
            PROPOSED DOMAIN TASKS ({activeTasks.length}/{initialPlan.length} active)
          </span>
          {isModified && (
            <button
              onClick={() => setRemovedTaskIds(new Set())}
              disabled={isSubmitting}
              className="text-amber-400 hover:text-amber-300 flex items-center space-x-1 transition"
            >
              <Undo2 className="w-3.5 h-3.5" />
              <span>Reset to original plan</span>
            </button>
          )}
        </div>

        {initialPlan.map((task, idx) => {
          const isRemoved = removedTaskIds.has(task.task_id);
          const domainInfo = DOMAIN_CONFIG[task.domain] || {
            label: task.domain.replace("_", " ").toUpperCase(),
            badgeClass: "bg-zinc-800 text-zinc-300 border-zinc-700",
            borderClass: "border-l-zinc-500",
          };

          return (
            <div
              key={task.task_id}
              className={`transition-all duration-200 border rounded-xl p-5 ${
                isRemoved
                  ? "bg-black/20 border-white/[0.04] opacity-50"
                  : `bg-surface border-white/[0.08] ${domainInfo.borderClass} border-l-4 shadow-md`
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${domainInfo.badgeClass}`}
                    >
                      {domainInfo.label}
                    </span>
                    <span className="text-[11px] font-mono text-zinc-400 bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.04]">
                      {task.task_id}
                    </span>
                    {isRemoved && (
                      <span className="text-[11px] font-medium text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                        Excluded from research
                      </span>
                    )}
                  </div>

                  <p
                    className={`text-sm leading-relaxed ${
                      isRemoved ? "line-through text-zinc-400" : "text-zinc-200 font-normal"
                    }`}
                  >
                    {task.description}
                  </p>

                  {/* Target Questions / Search Queries Pill Preview */}
                  {!isRemoved && task.search_queries && task.search_queries.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/[0.05] flex flex-wrap items-center gap-1.5 text-xs text-zinc-400">
                      <span className="text-zinc-400 flex items-center space-x-1">
                        <Search className="w-3 h-3 text-zinc-400" />
                        <span>Search queries:</span>
                      </span>
                      {task.search_queries.map((q, qIdx) => (
                        <span
                          key={qIdx}
                          className="px-2 py-0.5 rounded bg-black/40 text-zinc-400 text-[11px] font-mono border border-white/[0.04]"
                        >
                          &ldquo;{q}&rdquo;
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Remove / Restore Action */}
                <div className="flex-shrink-0 pt-0.5">
                  <button
                    onClick={() => toggleRemoveTask(task.task_id)}
                    disabled={isSubmitting}
                    className={`p-2 rounded-lg text-xs font-medium transition flex items-center space-x-1.5 ${
                      isRemoved
                        ? "bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-white/[0.04] hover:bg-rose-500/15 text-zinc-400 hover:text-rose-300 hover:border-rose-500/30 border border-white/[0.06]"
                    }`}
                    title={isRemoved ? "Restore task to agenda" : "Remove task from agenda"}
                  >
                    {isRemoved ? (
                      <>
                        <Undo2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Restore</span>
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Remove</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Footer */}
      <div className="sticky bottom-6 bg-surface/90 backdrop-blur-md border border-white/[0.12] rounded-xl p-4 sm:p-5 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-zinc-300 text-center sm:text-left">
          <div className="font-semibold text-white">
            {isModified ? (
              <span className="text-amber-400">
                Modified agenda: {activeTasks.length} of {initialPlan.length} tasks selected
              </span>
            ) : (
              <span>Full agenda: {initialPlan.length} tasks ready for execution</span>
            )}
          </div>
          <div className="text-zinc-400 mt-0.5">
            Approving will fan-out parallel web research workers across {activeTasks.length} domains.
          </div>
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-2.5 rounded-lg font-semibold text-sm transition shadow-lg ${
              isModified
                ? "bg-amber-500 hover:bg-amber-400 text-black active:bg-amber-600"
                : "bg-emerald-500 hover:bg-emerald-400 text-black active:bg-emerald-600"
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-black" />
                <span>Launching Researchers...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 text-black" />
                <span>
                  {isModified
                    ? `Approve Modified Plan (${activeTasks.length} Tasks)`
                    : `Approve Full Plan (${initialPlan.length} Tasks)`}
                </span>
                <ArrowRight className="w-4 h-4 text-black" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
