"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, Download, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";

interface FinalReportViewProps {
  companyName: string;
  threadId: string;
  finalReport: string;
  onNewAnalysis: () => void;
}

export function FinalReportView({
  companyName,
  threadId,
  finalReport,
  onNewAnalysis,
}: FinalReportViewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(finalReport);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy report:", err);
    }
  };

  const handleDownload = () => {
    const safeName = companyName.toLowerCase().replace(/[^a-z0-9]/g, "-");
    const blob = new Blob([finalReport], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `competitor-iq-${safeName}-report.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Top Completion Header */}
      <div className="bg-surface border border-emerald-500/30 rounded-xl p-6 mb-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 relative">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Analysis Complete</span>
              </span>
              <span className="text-xs text-zinc-400 font-mono">
                Session: {threadId}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Competitive Intelligence Dossier: <span className="text-amber-400">{companyName}</span>
            </h1>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1 max-w-2xl">
              Fully approved executive dossier. Ground-truth web evidence synthesized and citation-verified across pricing, features, customer sentiment, and strategic vulnerabilities.
            </p>
          </div>

          <div className="flex items-center space-x-2 self-start sm:self-center">
            <button
              onClick={onNewAnalysis}
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.1] text-xs font-semibold text-white transition shadow"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Analysis</span>
            </button>
          </div>
        </div>

        {/* Action Toolbar */}
        <div className="mt-6 pt-4 border-t border-white/[0.06] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2 text-zinc-400 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Dual Checkpoint Verified (Plan & Draft Approved)</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.08] text-zinc-200 hover:text-white transition"
              title="Copy Markdown to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-300">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Copy Markdown</span>
                </>
              )}
            </button>

            <button
              onClick={handleDownload}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-black/40 hover:bg-black/60 border border-white/[0.08] text-zinc-200 hover:text-white transition"
              title="Download report as markdown file"
            >
              <Download className="w-3.5 h-3.5 text-zinc-400" />
              <span>Download (.md)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Final Markdown Report Body */}
      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 sm:p-12 mb-12 shadow-2xl">
        <div className="prose prose-invert prose-zinc max-w-none text-sm sm:text-base leading-relaxed prose-headings:text-white prose-headings:font-bold prose-h1:text-3xl prose-h2:text-2xl prose-h2:border-b prose-h2:border-white/[0.08] prose-h2:pb-3 prose-h2:mt-10 prose-h3:text-lg prose-h3:text-amber-300 prose-p:text-zinc-200 prose-li:text-zinc-200 prose-strong:text-white prose-code:text-amber-300 prose-code:bg-white/[0.06] prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
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
            {finalReport}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
