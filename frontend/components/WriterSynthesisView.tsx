"use client";

import React from "react";
import { Loader2, FileText, CheckCircle2, MessageSquareQuote, Sparkles } from "lucide-react";

interface WriterSynthesisViewProps {
  companyName: string;
  reason?: "initial" | "revision";
  feedback?: string | null;
  revisionRound?: number;
}

export function WriterSynthesisView({
  companyName,
  reason = "initial",
  feedback,
  revisionRound = 1,
}: WriterSynthesisViewProps) {
  const isRevision = reason === "revision" || !!feedback;

  return (
    <div className="w-full max-w-3xl mx-auto py-16 px-4 sm:px-6 text-center">
      <div className="bg-surface border border-white/[0.08] rounded-xl p-8 sm:p-10 shadow-2xl relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 mb-6">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>

          <div className="inline-flex items-center space-x-2 text-xs font-mono px-3 py-1 rounded-full bg-white/[0.04] text-zinc-300 border border-white/[0.06] mb-4">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>
              {isRevision
                ? `Writer Agent: Revision Pass ${revisionRound > 1 ? `#${revisionRound}` : ""}`
                : "Writer Agent: Synthesis Pass"}
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">
            {isRevision ? (
              <>
                Regenerating Report for <span className="text-amber-400">{companyName}</span>
              </>
            ) : (
              <>
                Synthesizing Dossier for <span className="text-amber-400">{companyName}</span>
              </>
            )}
          </h2>

          <p className="text-sm text-zinc-400 max-w-md mx-auto mb-6">
            {isRevision
              ? "Applying requested feedback, re-grounding factual claims against web evidence, and revising report sections."
              : "All researcher findings have fanned-in. The Writer node is cross-correlating domain evidence, enforcing citation grounding, and structuring executive intelligence."}
          </p>

          {/* Feedback Display if in revision loop */}
          {feedback && (
            <div className="mb-6 p-4 rounded-xl bg-black/40 border border-amber-500/30 text-left max-w-lg mx-auto">
              <div className="flex items-center space-x-2 text-xs font-semibold text-amber-300 mb-1">
                <MessageSquareQuote className="w-4 h-4 text-amber-400" />
                <span>Incorporating Revision Instructions:</span>
              </div>
              <p className="text-xs text-zinc-300 font-mono italic leading-relaxed pl-6">
                &ldquo;{feedback}&rdquo;
              </p>
            </div>
          )}

          {/* Synthesis Stages */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left max-w-lg mx-auto">
            <div className="p-3 rounded-lg bg-black/30 border border-emerald-500/30 flex items-center space-x-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="text-xs text-zinc-200">Evidence Fanned-In</span>
            </div>
            <div className="p-3 rounded-lg bg-black/30 border border-amber-500/40 flex items-center space-x-2.5">
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin flex-shrink-0" />
              <span className="text-xs text-zinc-200">Grounding Citations</span>
            </div>
            <div className="p-3 rounded-lg bg-black/30 border border-white/[0.06] flex items-center space-x-2.5 opacity-60">
              <FileText className="w-4 h-4 text-zinc-400 flex-shrink-0" />
              <span className="text-xs text-zinc-300">Formatting Markdown</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
