/**
 * CompetitorIQ Frontend Types & SSE Protocol Definitions
 * Based on docs/SSE_API_SPEC.md (Phase 5 Contract)
 */

export type ResearchDomain =
  | "pricing_packaging"
  | "feature_set"
  | "customer_sentiment"
  | "news_funding"
  | "positioning_messaging"
  | string;

export interface ResearchTask {
  task_id: string;
  domain: ResearchDomain;
  description: string;
  search_queries: string[];
  target_questions: string[];
}

export type PipelinePhase =
  | "idle"
  | "initializing"
  | "planning"
  | "awaiting_plan_approval"
  | "researching"
  | "synthesizing"
  | "awaiting_draft_approval"
  | "completed"
  | "error";

export interface SessionCreatedPayload {
  thread_id: string;
  company_name: string;
  company_url: string | null;
}

export interface PlannerStartedPayload {
  company_name: string;
}

export interface PlanReadyPayload {
  thread_id: string;
  research_plan: ResearchTask[];
}

export interface AwaitingApprovalPayload {
  checkpoint: "plan" | "draft";
  thread_id: string;
  company_name: string;
  data: {
    research_plan?: ResearchTask[];
    report_draft?: string;
  };
}

export interface ResearcherStartedPayload {
  task_id: string;
  domain: string;
  queries: string[];
}

export interface SourceRef {
  title: string;
  url: string;
}

export interface ResearcherFinishedPayload {
  task_id: string;
  domain: string;
  confidence: number;
  sources_count: number;
  top_insight: string;
  sources: SourceRef[];
}

export interface WriterStartedPayload {
  reason: "initial" | "revision";
  feedback?: string;
}

export interface WriterFinishedPayload {
  draft_length: number;
  report_draft: string;
}

export interface ReportReadyPayload {
  thread_id: string;
  final_report: string;
}

export interface DonePayload {
  thread_id: string;
  status: "awaiting_approval" | "complete";
}

export interface ErrorPayload {
  message: string;
  type: string;
}

export interface LiveResearcherItem {
  task_id: string;
  domain: string;
  status: "running" | "finished";
  queries?: string[];
  top_insight?: string;
  confidence?: number;
  sources_count?: number;
  sources?: SourceRef[];
}

