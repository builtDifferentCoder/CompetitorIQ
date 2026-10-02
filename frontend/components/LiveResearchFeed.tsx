"use client";

import React, { useState } from "react";
import { LiveResearcherItem } from "@/lib/types";
import { Globe, CheckCircle2, Search, ExternalLink, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

interface LiveResearchFeedProps {
  companyName: string;
  threadId: string;
  totalPlannedTasks: number;
  researchers: LiveResearcherItem[];
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

export function LiveResearchFeed({
  companyName,
  threadId,
  totalPlannedTasks,
  researchers,
}: LiveResearchFeedProps) {
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const toggleSources = (taskId: string) => {
    setExpandedSources((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const finishedCount = researchers.filter((r) => r.status === "finished").length;
  const progressPercent = totalPlannedTasks > 0 ? Math.round((finishedCount / totalPlannedTasks) * 100) : 0;

  return (
    <div className="w-full max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Feed Header */}
      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 mb-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center space-x-2 mb-1.5">
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                <span>Live Parallel Research</span>
              </span>
              <span className="text-xs text-zinc-400 font-mono">
                Tavily Search API &middot; LangGraph Send
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Investigating <span className="text-amber-400">{companyName}</span>
            </h2>
            <p className="text-xs sm:text-sm text-zinc-400 mt-0.5">
              Domain agents are executing web queries concurrently. Findings stream into state as each worker completes.
            </p>
          </div>

          <div className="text-right sm:text-right self-start sm:self-center">
            <div className="text-sm font-semibold text-white font-mono">
              {finishedCount} of {totalPlannedTasks || researchers.length} Agents Finished
            </div>
            <div className="text-xs text-zinc-400 font-mono">
              Session: {threadId}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-black/40 h-2 rounded-full overflow-hidden border border-white/[0.05]">
          <div
            className="bg-amber-400 h-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Cards List in Natural Arrival Order */}
      <div className="space-y-4">
        {researchers.length === 0 && (
          <div className="text-center py-12 bg-surface/50 border border-white/[0.06] rounded-xl">
            <Loader2 className="w-6 h-6 animate-spin text-amber-400 mx-auto mb-2" />
            <div className="text-sm text-zinc-300">Dispatching worker agents...</div>
          </div>
        )}

        {researchers.map((item) => {
          const domainInfo = DOMAIN_CONFIG[item.domain] || {
            label: item.domain.replace("_", " ").toUpperCase(),
            badgeClass: "bg-zinc-800 text-zinc-300 border-zinc-700",
            borderClass: "border-l-zinc-500",
          };

          const isRunning = item.status === "running";
          const confidencePercent = item.confidence ? Math.round(item.confidence * 100) : 0;
          const showSources = !!expandedSources[item.task_id];

          return (
            <div
              key={item.task_id}
              className={`transition-all duration-300 border rounded-xl p-5 ${
                isRunning
                  ? `bg-surface/80 border-white/[0.08] ${domainInfo.borderClass} border-l-4 shadow-md`
                  : `bg-surface border-white/[0.08] ${domainInfo.borderClass} border-l-4 shadow-lg`
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${domainInfo.badgeClass}`}
                  >
                    {domainInfo.label}
                  </span>
                  <span className="text-[11px] font-mono text-zinc-400 bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.04]">
                    {item.task_id}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  {isRunning ? (
                    <span className="inline-flex items-center space-x-1.5 text-xs text-amber-300 font-medium bg-amber-500/10 px-2.5 py-0.5 rounded-full border border-amber-500/20">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                      <span>Web Searching...</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 text-xs text-emerald-400 font-medium bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Evidence Gathered</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Running State: Queries & Shimmer */}
              {isRunning && (
                <div className="space-y-3">
                  <div className="space-y-2 py-1">
                    <div className="h-4 bg-white/[0.06] rounded animate-pulse w-5/6" />
                    <div className="h-4 bg-white/[0.04] rounded animate-pulse w-3/4" />
                  </div>

                  {item.queries && item.queries.length > 0 && (
                    <div className="pt-2 border-t border-white/[0.05] flex flex-wrap items-center gap-1.5 text-xs text-zinc-400">
                      <span className="text-zinc-400 flex items-center space-x-1">
                        <Search className="w-3 h-3 text-zinc-400" />
                        <span>Active queries:</span>
                      </span>
                      {item.queries.map((q, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-black/40 text-zinc-400 text-[11px] font-mono border border-white/[0.04]"
                        >
                          &ldquo;{q}&rdquo;
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Finished State: Top Insight, Confidence & Sources */}
              {!isRunning && (
                <div>
                  <div className="text-sm text-zinc-100 font-normal leading-relaxed mb-4">
                    {item.top_insight}
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/[0.06] text-xs">
                    <div className="flex items-center space-x-4">
                      {/* Confidence Meter */}
                      <div className="flex items-center space-x-2">
                        <span className="text-zinc-400">Confidence:</span>
                        <div className="flex items-center space-x-1.5">
                          <div className="w-16 bg-black/50 h-2 rounded-full overflow-hidden border border-white/[0.06]">
                            <div
                              className="bg-emerald-400 h-full rounded-full"
                              style={{ width: `${confidencePercent}%` }}
                            />
                          </div>
                          <span className="font-mono font-medium text-emerald-400">
                            {confidencePercent}%
                          </span>
                        </div>
                      </div>

                      {/* Source Count */}
                      <div className="text-zinc-400">
                        <span className="text-zinc-200 font-mono font-medium">{item.sources_count ?? item.sources?.length ?? 0}</span> sources verified
                      </div>
                    </div>

                    {item.sources && item.sources.length > 0 && (
                      <button
                        onClick={() => toggleSources(item.task_id)}
                        className="text-amber-400 hover:text-amber-300 inline-flex items-center space-x-1 transition text-xs"
                      >
                        <span>{showSources ? "Hide sources" : "View source URLs"}</span>
                        {showSources ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                  </div>

                  {/* Expandable Source Links */}
                  {showSources && item.sources && item.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-white/[0.05] space-y-1.5">
                      <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                        CITED DOMAIN SOURCES
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {item.sources.map((src, sIdx) => (
                          <a
                            key={sIdx}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center space-x-2 p-2 rounded bg-black/30 hover:bg-black/50 border border-white/[0.04] hover:border-white/[0.1] text-xs text-zinc-300 hover:text-white transition truncate group"
                          >
                            <ExternalLink className="w-3 h-3 text-zinc-400 group-hover:text-amber-400 flex-shrink-0" />
                            <span className="truncate">{src.title || src.url}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
