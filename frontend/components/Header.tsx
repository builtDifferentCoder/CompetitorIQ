"use client";

import React from "react";
import { Sparkles, RotateCcw } from "lucide-react";

interface HeaderProps {
  threadId?: string | null;
  onReset?: () => void;
  isRunning?: boolean;
}

export function Header({ threadId, onReset, isRunning }: HeaderProps) {
  return (
    <header className="w-full border-b border-white/[0.07] bg-surface/50 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shadow-inner">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-semibold tracking-tight text-white text-base">
                Competitor<span className="text-amber-400">IQ</span>
              </span>
              <span className="text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-white/[0.06] text-zinc-400 border border-white/[0.05]">
                v1.0
              </span>
            </div>
            <span className="text-[11px] text-zinc-400 font-normal">
              Autonomous Competitive Intelligence
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {threadId && (
            <div className="hidden sm:flex items-center space-x-2 text-xs font-mono text-zinc-400 bg-white/[0.04] px-2.5 py-1 rounded-md border border-white/[0.06]">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>Session:</span>
              <span className="text-zinc-200">{threadId}</span>
            </div>
          )}

          {threadId && onReset && (
            <button
              onClick={onReset}
              disabled={isRunning}
              className="text-xs text-zinc-300 hover:text-white px-3 py-1.5 rounded-md bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] transition flex items-center space-x-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
              title="Start a new analysis"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Run</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
