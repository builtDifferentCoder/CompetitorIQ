"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CheckCircle2, MessageSquare, ShieldCheck, ArrowRight, Loader2, Sparkles, AlertCircle } from "lucide-react";

interface DraftReviewProps {
  companyName: string;
  threadId: string;
  reportDraft: string;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isSubmitting: boolean;
  revisionRound?: number;
}

export function DraftReview({
  companyName,
  threadId,
  reportDraft,
  onApprove,
  onRequestChanges,
  isSubmitting,
  revisionRound = 1,
}: DraftReviewProps) {
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");

  const handleRequestChangesSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackText.trim() || isSubmitting) return;
    onRequestChanges(feedbackText.trim());
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Checkpoint 2 Header Banner */}
      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 mb-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                Checkpoint 2
              </span>
              <span className="text-xs text-zinc-400 font-mono">
                Draft Review & Grounding Check
              </span>
              {revisionRound > 1 && (
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Revision #{revisionRound}
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Preliminary Dossier for <span className="text-amber-400">{companyName}</span>
            </h2>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1 max-w-2xl">
              The Writer node has synthesized research findings. Every claim is grounded with inline citations [X] referencing Tavily evidence. You may approve the draft or request targeted changes.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono text-zinc-400 bg-white/[0.03] px-3 py-2 rounded-lg border border-white/[0.06] self-start sm:self-center">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Draft Intercepted</span>
          </div>
        </div>
      </div>

      {/* Markdown Report Document */}
      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 sm:p-10 mb-8 shadow-2xl">
        <div className="flex items-center justify-between pb-4 mb-6 border-b border-white/[0.08] text-xs font-mono text-zinc-400">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>EXECUTIVE SYNTHESIS PREVIEW</span>
          </div>
          <div>{reportDraft.length.toLocaleString()} characters</div>
        </div>

        <div className="prose prose-invert prose-zinc max-w-none text-sm sm:text-base leading-relaxed prose-headings:text-white prose-headings:font-bold prose-h1:text-2xl prose-h2:text-xl prose-h2:border-b prose-h2:border-white/[0.08] prose-h2:pb-2 prose-h2:mt-8 prose-h3:text-base prose-h3:text-amber-300 prose-p:text-zinc-200 prose-li:text-zinc-200 prose-strong:text-white prose-code:text-amber-300 prose-code:bg-white/[0.06] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom citation link styling for inline [1], [2]
              a: ({ node, ...props }) => (
                <a
                  {...props}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-400 hover:text-amber-300 underline underline-offset-2 break-all font-mono text-xs"
                />
              ),
            }}
          >
            {reportDraft}
          </ReactMarkdown>
        </div>
      </div>

      {/* Request Changes Drawer */}
      {showFeedbackInput && (
        <div className="bg-surface border border-amber-500/30 rounded-xl p-6 mb-6 shadow-2xl">
          <div className="flex items-center space-x-2 mb-2 text-sm font-semibold text-amber-300">
            <MessageSquare className="w-4 h-4 text-amber-400" />
            <span>Request Specific Changes & Revisions</span>
          </div>
          <p className="text-xs text-zinc-400 mb-3">
            Instruct the Writer node how to improve the draft. The agent will re-examine the gathered evidence, rewrite relevant sections, and present an updated draft at Checkpoint 2.
          </p>

          <form onSubmit={handleRequestChangesSubmit} className="space-y-3">
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="e.g. Focus more on enterprise packaging and security certifications, expand on the churn drivers in customer sentiment, or compare pricing directly with Datadog."
              rows={3}
              disabled={isSubmitting}
              required
              className="w-full p-3 bg-black/50 border border-white/[0.1] focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/40 rounded-lg text-sm text-white placeholder-zinc-500 outline-none transition disabled:opacity-50"
            />

            <div className="flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowFeedbackInput(false)}
                disabled={isSubmitting}
                className="px-3.5 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!feedbackText.trim() || isSubmitting}
                className="inline-flex items-center space-x-2 px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-black font-semibold text-xs transition disabled:opacity-40"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Sending Feedback...</span>
                  </>
                ) : (
                  <>
                    <span>Submit Revision Request</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Action Footer Bar */}
      <div className="sticky bottom-6 bg-surface/90 backdrop-blur-md border border-white/[0.12] rounded-xl p-4 sm:p-5 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-zinc-300 text-center sm:text-left">
          <div className="font-semibold text-white">
            Human Approval Required to Finalize Dossier
          </div>
          <div className="text-zinc-400 mt-0.5">
            Approve to produce final publication report, or request revisions to guide the Writer agent.
          </div>
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          {!showFeedbackInput && (
            <button
              onClick={() => setShowFeedbackInput(true)}
              disabled={isSubmitting}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-4 py-2.5 rounded-lg font-medium text-xs text-zinc-300 hover:text-white bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] transition disabled:opacity-40"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Request Changes</span>
            </button>
          )}

          <button
            onClick={onApprove}
            disabled={isSubmitting}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-black font-semibold text-sm transition shadow-lg disabled:opacity-40"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-black" />
                <span>Finalizing...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 text-black" />
                <span>Approve & Finalize Report</span>
                <ArrowRight className="w-4 h-4 text-black" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
