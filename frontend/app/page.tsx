"use client";

import React, { useState, useRef } from "react";
import { Header } from "@/components/Header";
import { CompanyInput } from "@/components/CompanyInput";
import { PlanReview } from "@/components/PlanReview";
import { LiveResearchFeed } from "@/components/LiveResearchFeed";
import { WriterSynthesisView } from "@/components/WriterSynthesisView";
import { DraftReview } from "@/components/DraftReview";
import { FinalReportView } from "@/components/FinalReportView";
import { API_ROUTES } from "@/lib/config";
import { consumeSSEStream } from "@/lib/sse-client";
import {
  ResearchTask,
  PipelinePhase,
  LiveResearcherItem,
} from "@/lib/types";
import { Loader2, Sparkles } from "lucide-react";

export default function Home() {
  const [phase, setPhase] = useState<PipelinePhase>("idle");
  const [companyName, setCompanyName] = useState<string>("");
  const [companyUrl, setCompanyUrl] = useState<string | undefined>(undefined);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [researchPlan, setResearchPlan] = useState<ResearchTask[]>([]);
  const [researchers, setResearchers] = useState<LiveResearcherItem[]>([]);
  const [reportDraft, setReportDraft] = useState<string>("");
  const [finalReport, setFinalReport] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Revision tracking
  const [revisionRound, setRevisionRound] = useState<number>(1);
  const [currentFeedback, setCurrentFeedback] = useState<string | null>(null);
  const [writerReason, setWriterReason] = useState<"initial" | "revision">("initial");

  const abortControllerRef = useRef<AbortController | null>(null);

  // Central event router for SSE streams
  const handleIncomingEvent = (eventName: string, data: any) => {
    switch (eventName) {
      case "session_created":
        if (data?.thread_id) {
          setThreadId(data.thread_id);
        }
        break;

      case "planner_started":
        // Planner actively constructing domain tasks
        break;

      case "plan_ready":
        if (data?.research_plan) {
          setResearchPlan(data.research_plan);
        }
        break;

      case "awaiting_approval":
        if (data?.checkpoint === "plan") {
          if (data?.data?.research_plan) {
            setResearchPlan(data.data.research_plan);
          }
          setPhase("awaiting_plan_approval");
        } else if (data?.checkpoint === "draft") {
          if (data?.data?.report_draft) {
            setReportDraft(data.data.report_draft);
          }
          setPhase("awaiting_draft_approval");
        }
        break;

      case "researcher_started":
        if (data?.task_id) {
          setPhase("researching");
          setResearchers((prev) => {
            const existingIdx = prev.findIndex((r) => r.task_id === data.task_id);
            if (existingIdx >= 0) {
              const updated = [...prev];
              updated[existingIdx] = {
                ...updated[existingIdx],
                status: "running",
                queries: data.queries || [],
                domain: data.domain || updated[existingIdx].domain,
              };
              return updated;
            }
            return [
              ...prev,
              {
                task_id: data.task_id,
                domain: data.domain || "research",
                status: "running",
                queries: data.queries || [],
              },
            ];
          });
        }
        break;

      case "researcher_finished":
        if (data?.task_id) {
          setResearchers((prev) => {
            const existingIdx = prev.findIndex((r) => r.task_id === data.task_id);
            if (existingIdx >= 0) {
              const updated = [...prev];
              updated[existingIdx] = {
                ...updated[existingIdx],
                status: "finished",
                domain: data.domain || updated[existingIdx].domain,
                confidence: data.confidence,
                sources_count: data.sources_count,
                top_insight: data.top_insight,
                sources: data.sources || [],
              };
              return updated;
            }
            return [
              ...prev,
              {
                task_id: data.task_id,
                domain: data.domain || "research",
                status: "finished",
                confidence: data.confidence,
                sources_count: data.sources_count,
                top_insight: data.top_insight,
                sources: data.sources || [],
              },
            ];
          });
        }
        break;

      case "writer_started":
        setWriterReason(data?.reason === "revision" ? "revision" : "initial");
        if (data?.feedback) {
          setCurrentFeedback(data.feedback);
        }
        setPhase("synthesizing");
        break;

      case "writer_finished":
        if (data?.report_draft) {
          setReportDraft(data.report_draft);
        }
        break;

      case "report_ready":
        if (data?.final_report) {
          setFinalReport(data.final_report);
          setPhase("completed");
        }
        break;

      case "done":
        if (data?.status === "complete") {
          setPhase("completed");
        }
        setIsSubmitting(false);
        break;

      case "error":
        setError(data?.message || "An unexpected error occurred.");
        setIsSubmitting(false);
        break;
    }
  };

  // 1. Initial /analyze call
  const handleStartAnalysis = async (targetName: string, targetUrl?: string) => {
    setError(null);
    setCompanyName(targetName);
    setCompanyUrl(targetUrl);
    setPhase("planning");
    setResearchPlan([]);
    setResearchers([]);
    setReportDraft("");
    setFinalReport("");
    setThreadId(null);
    setRevisionRound(1);
    setCurrentFeedback(null);

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await consumeSSEStream(
        API_ROUTES.analyze,
        {
          company_name: targetName,
          company_url: targetUrl || null,
        },
        {
          onEvent: handleIncomingEvent,
          onError: (err) => {
            setError(err.message || "Failed to connect to backend server.");
            setPhase("idle");
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      setError(err.message || "Network error connecting to analysis backend.");
      setPhase("idle");
    }
  };

  // 2. Checkpoint 1: Approve Full Plan
  const handleApprovePlan = async () => {
    if (!threadId || isSubmitting) return;
    setIsSubmitting(true);
    setPhase("researching");
    setResearchers([]);

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await consumeSSEStream(
        API_ROUTES.resume(threadId),
        { action: "approve" },
        {
          onEvent: handleIncomingEvent,
          onError: (err) => {
            console.error("Error during research phase:", err);
            setError(err.message);
            setIsSubmitting(false);
          },
          onDone: () => {
            setIsSubmitting(false);
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      console.error("Resume stream error:", err);
      setIsSubmitting(false);
    }
  };

  // 3. Checkpoint 1: Approve Modified Plan (Task Removal)
  const handleEditPlan = async (filteredPlan: ResearchTask[]) => {
    if (!threadId || isSubmitting) return;
    setIsSubmitting(true);
    setPhase("researching");
    setResearchPlan(filteredPlan);
    setResearchers([]);

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await consumeSSEStream(
        API_ROUTES.resume(threadId),
        {
          action: "edit",
          research_plan: filteredPlan,
        },
        {
          onEvent: handleIncomingEvent,
          onError: (err) => {
            console.error("Error during research phase:", err);
            setError(err.message);
            setIsSubmitting(false);
          },
          onDone: () => {
            setIsSubmitting(false);
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      console.error("Resume stream error:", err);
      setIsSubmitting(false);
    }
  };

  // 4. Checkpoint 2: Approve Draft
  const handleApproveDraft = async () => {
    if (!threadId || isSubmitting) return;
    setIsSubmitting(true);

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await consumeSSEStream(
        API_ROUTES.resume(threadId),
        { action: "approve" },
        {
          onEvent: handleIncomingEvent,
          onError: (err) => {
            console.error("Error finalizing report:", err);
            setError(err.message);
            setIsSubmitting(false);
          },
          onDone: () => {
            setIsSubmitting(false);
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      console.error("Approve draft stream error:", err);
      setIsSubmitting(false);
    }
  };

  // 5. Checkpoint 2: Request Changes (Revision Loop)
  const handleRequestChanges = async (feedback: string) => {
    if (!threadId || isSubmitting) return;
    setIsSubmitting(true);
    setWriterReason("revision");
    setCurrentFeedback(feedback);
    setRevisionRound((r) => r + 1);
    setPhase("synthesizing");

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await consumeSSEStream(
        API_ROUTES.resume(threadId),
        {
          action: "request_changes",
          feedback,
        },
        {
          onEvent: handleIncomingEvent,
          onError: (err) => {
            console.error("Error requesting changes:", err);
            setError(err.message);
            setIsSubmitting(false);
          },
          onDone: () => {
            setIsSubmitting(false);
          },
        },
        abortController.signal
      );
    } catch (err: any) {
      console.error("Request changes stream error:", err);
      setIsSubmitting(false);
    }
  };

  // 6. Reset & Start New Analysis
  const handleReset = () => {
    abortControllerRef.current?.abort();
    setPhase("idle");
    setCompanyName("");
    setCompanyUrl(undefined);
    setThreadId(null);
    setResearchPlan([]);
    setResearchers([]);
    setReportDraft("");
    setFinalReport("");
    setError(null);
    setIsSubmitting(false);
    setRevisionRound(1);
    setCurrentFeedback(null);
    setWriterReason("initial");
  };

  const isPipelineRunning =
    phase === "planning" || phase === "researching" || phase === "synthesizing";

  return (
    <div className="min-h-screen flex flex-col bg-background text-zinc-100">
      <Header
        threadId={threadId}
        onReset={handleReset}
        isRunning={isPipelineRunning}
      />

      <main className="flex-1 flex flex-col justify-center">
        {phase === "idle" && (
          <CompanyInput
            onSubmit={handleStartAnalysis}
            isLoading={false}
            error={error}
          />
        )}

        {phase === "planning" && (
          <div className="w-full max-w-lg mx-auto py-20 px-4 text-center">
            <div className="bg-surface border border-white/[0.08] rounded-xl p-8 shadow-2xl">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 mb-5">
                <Loader2 className="w-7 h-7 animate-spin" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">
                Analyzing <span className="text-amber-400">{companyName}</span>
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 max-w-sm mx-auto mb-6">
                Planner agent is decomposing the competitive landscape and generating targeted research tasks...
              </p>
              <div className="flex items-center justify-center space-x-2 text-xs font-mono text-zinc-400 bg-white/[0.03] py-2 px-3 rounded-lg border border-white/[0.05]">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Anthropic Claude 3.5 Sonnet</span>
              </div>
            </div>
          </div>
        )}

        {phase === "awaiting_plan_approval" && (
          <PlanReview
            companyName={companyName}
            threadId={threadId || ""}
            initialPlan={researchPlan}
            onApprove={handleApprovePlan}
            onEdit={handleEditPlan}
            isSubmitting={isSubmitting}
          />
        )}

        {phase === "researching" && (
          <LiveResearchFeed
            companyName={companyName}
            threadId={threadId || ""}
            totalPlannedTasks={researchPlan.length}
            researchers={researchers}
          />
        )}

        {phase === "synthesizing" && (
          <WriterSynthesisView
            companyName={companyName}
            reason={writerReason}
            feedback={currentFeedback}
            revisionRound={revisionRound}
          />
        )}

        {phase === "awaiting_draft_approval" && (
          <DraftReview
            companyName={companyName}
            threadId={threadId || ""}
            reportDraft={reportDraft}
            onApprove={handleApproveDraft}
            onRequestChanges={handleRequestChanges}
            isSubmitting={isSubmitting}
            revisionRound={revisionRound}
          />
        )}

        {phase === "completed" && (
          <FinalReportView
            companyName={companyName}
            threadId={threadId || ""}
            finalReport={finalReport || reportDraft}
            onNewAnalysis={handleReset}
          />
        )}
      </main>

      <footer className="border-t border-white/[0.05] py-4 text-center text-xs text-zinc-400">
        CompetitorIQ &mdash; Phase 6 Complete (Full Interactive Dashboard)
      </footer>
    </div>
  );
}
