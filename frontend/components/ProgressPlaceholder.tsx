"use client";

import React from "react";
import { Loader2, Globe, Cpu, FileText, CheckCircle2 } from "lucide-react";

interface ProgressPlaceholderProps {
  companyName: string;
  threadId: string;
  phase: string;
  isDraftReady?: boolean;
}

export function ProgressPlaceholder({
  companyName,
  threadId,
  phase,
  isDraftReady,
}: ProgressPlaceholderProps) {
  return (
    <div className="w-full max-w-2xl mx-auto py-16 px-4 sm:px-6 text-center">
      <div className="bg-surface border border-white/[0.08] rounded-xl p-8 shadow-2xl">
        <div className="relative inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 mb-6">
          <Loader2 className="w-8 h-8 animate-spin" />
          <div className="absolute inset-0 rounded-2xl border border-amber-400/20 animate-ping opacity-25" />
        </div>

        <div className="inline-flex items-center space-x-2 text-xs font-mono px-3 py-1 rounded-full bg-white/[0.04] text-zinc-300 border border-white/[0.06] mb-4">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Session: {threadId}</span>
        </div>

        <h2 className="text-2xl font-bold text-white tracking-tight mb-2">
          Executing Research on <span className="text-amber-400">{companyName}</span>
        </h2>
        <p className="text-sm text-zinc-400 max-w-md mx-auto mb-8">
          The plan was approved. Parallel research workers are querying Tavily, collecting web evidence, and extracting grounded findings.
        </p>

        {/* Milestone Steps */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
          <div className="p-3.5 rounded-lg bg-black/40 border border-emerald-500/30 flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-emerald-300">Plan Approved</div>
              <div className="text-[11px] text-zinc-400">Checkpoint 1 cleared</div>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-black/40 border border-amber-500/40 flex items-center space-x-3">
            <Globe className="w-5 h-5 text-amber-400 flex-shrink-0 animate-pulse" />
            <div>
              <div className="text-xs font-semibold text-amber-300">Parallel Research</div>
              <div className="text-[11px] text-zinc-400">Gathering web sources</div>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-black/40 border border-white/[0.06] flex items-center space-x-3 opacity-60">
            <FileText className="w-5 h-5 text-zinc-400 flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-zinc-300">Writer Synthesis</div>
              <div className="text-[11px] text-zinc-400">Awaiting fan-in</div>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-white/[0.06] text-xs text-zinc-400">
          <span className="font-mono text-zinc-400">Phase 6, Part 1 Complete:</span> Checkpoint 1 approved. Part 2 will render the live parallel researcher cards and streaming writer view here.
        </div>
      </div>
    </div>
  );
}
