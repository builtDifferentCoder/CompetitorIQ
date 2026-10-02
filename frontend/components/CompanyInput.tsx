"use client";

import React, { useState } from "react";
import { ArrowRight, Globe, Building2, AlertCircle, Loader2 } from "lucide-react";
import { BACKEND_URL } from "@/lib/config";

interface CompanyInputProps {
  onSubmit: (companyName: string, companyUrl?: string) => void;
  isLoading: boolean;
  error?: string | null;
}

const SAMPLE_COMPANIES = ["Linear", "Figma", "Notion", "Retool", "Supabase"];

export function CompanyInput({ onSubmit, isLoading, error }: CompanyInputProps) {
  const [companyName, setCompanyName] = useState("");
  const [companyUrl, setCompanyUrl] = useState("");
  const [showUrlField, setShowUrlField] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || isLoading) return;
    onSubmit(companyName.trim(), companyUrl.trim() || undefined);
  };

  const handleSelectSample = (name: string) => {
    setCompanyName(name);
  };

  return (
    <div className="w-full max-w-2xl mx-auto py-12 px-4 sm:px-6">
      <div className="text-center mb-8">
        <div className="inline-flex items-center space-x-2 text-xs font-medium px-3 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          <span>Multi-Agent Competitive Intelligence</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white mb-3">
          Research any competitor with verifiable evidence
        </h1>
        <p className="text-zinc-400 text-sm sm:text-base max-w-lg mx-auto">
          Autonomous planning, parallel web exploration across 5 business domains, and human-verified report synthesis.
        </p>
      </div>

      <div className="bg-surface border border-white/[0.08] rounded-xl p-6 shadow-2xl shadow-black/40">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="company-name" className="block text-xs font-medium text-zinc-300 mb-1.5">
              Target Company Name <span className="text-amber-400">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-400">
                <Building2 className="w-4 h-4" />
              </div>
              <input
                id="company-name"
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Figma, Linear, Notion, Datadog..."
                disabled={isLoading}
                required
                className="w-full pl-10 pr-4 py-2.5 bg-black/40 border border-white/[0.08] focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/40 rounded-lg text-sm text-white placeholder-zinc-500 outline-none transition disabled:opacity-50"
              />
            </div>
          </div>

          {showUrlField && (
            <div>
              <label htmlFor="company-url" className="block text-xs font-medium text-zinc-300 mb-1.5">
                Official Website URL <span className="text-zinc-500">(Optional)</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-400">
                  <Globe className="w-4 h-4" />
                </div>
                <input
                  id="company-url"
                  type="url"
                  value={companyUrl}
                  onChange={(e) => setCompanyUrl(e.target.value)}
                  placeholder="https://example.com"
                  disabled={isLoading}
                  className="w-full pl-10 pr-4 py-2.5 bg-black/40 border border-white/[0.08] focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/40 rounded-lg text-sm text-white placeholder-zinc-500 outline-none transition disabled:opacity-50"
                />
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={() => setShowUrlField(!showUrlField)}
              disabled={isLoading}
              className="text-xs text-zinc-400 hover:text-zinc-300 underline underline-offset-4 transition"
            >
              {showUrlField ? "Hide website URL" : "+ Add website URL"}
            </button>

            <button
              type="submit"
              disabled={!companyName.trim() || isLoading}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-black font-semibold text-sm shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-black" />
                  <span>Initializing...</span>
                </>
              ) : (
                <>
                  <span>Start Analysis</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-5 border-t border-white/[0.06] flex items-center space-x-2 text-xs text-zinc-400">
          <span className="text-zinc-500">Quick test:</span>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLE_COMPANIES.map((company) => (
              <button
                key={company}
                type="button"
                onClick={() => handleSelectSample(company)}
                disabled={isLoading}
                className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.05] text-zinc-300 hover:text-white transition disabled:opacity-40"
              >
                {company}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
          <div className="flex-1">
            <div className="font-semibold text-rose-200">Unable to reach intelligence server</div>
            <div className="text-xs text-rose-300/90 mt-0.5">{error}</div>
            <div className="text-[11px] text-rose-400/70 mt-1">
              Ensure the FastAPI backend is running and reachable at <code>{BACKEND_URL}</code>.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
