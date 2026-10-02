# CompetitorIQ — Server-Sent Events (SSE) & REST API Specification
**Version:** Phase 5 (FastAPI Backend + SSE Streaming)  
**Target Consumer:** Phase 6 Next.js / React Frontend  

---

## 1. Architecture Overview

The CompetitorIQ backend exposes an HTTP REST + Server-Sent Events (SSE) API powered by FastAPI, Uvicorn, and LangGraph.

- **Non-blocking decoupled execution**: Graph runs inside a dedicated background worker daemon thread. A client disconnecting (network timeout, tab close, page refresh) does **not** terminate graph execution or corrupt checkpoints; execution continues to the next checkpoint and commits state to SQLite (`checkpoints.db`).
- **Checkpoint persistence**: Powered by `CompetitorIQSqliteSaver` across processes and requests.
- **Two human-in-the-loop checkpoints**:
  1. `Checkpoint 1: Plan Review` (`human_review` node)
  2. `Checkpoint 2: Draft Review` (`draft_review` node)

---

## 2. Endpoints Summary

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Starts competitive analysis for a target company; streams events to Checkpoint 1. |
| `POST` | `/resume/{thread_id}` | Resumes pipeline from pending checkpoint (Plan or Draft) with human action; streams events to next checkpoint or completion. |
| `GET` | `/status/{thread_id}` | Returns current thread state, status, plan, draft, and final report snapshot. |
| `GET` | `/health` | Health check endpoint returning service status. |

---

## 3. SSE Protocol & Event Vocabulary

All streamed responses from `/analyze` and `/resume/{thread_id}` use `Content-Type: text/event-stream`.  
Standard event framing format:
```text
event: <event_name>\n
data: <json_string>\n\n
```

### Event Catalog

| Event Name | Emitted When | Payload Schema | Description |
|---|---|---|---|
| `session_created` | Pipeline initialized | `{"thread_id": str, "company_name": str, "company_url": str \| null}` | First event; supplies the client with the persistent session/thread identifier. |
| `planner_started` | Planner begins prompt execution | `{"company_name": str}` | Signals the planner has started researching domains. |
| `plan_ready` | Planner completes research plan | `{"thread_id": str, "research_plan": list[ResearchTask]}` | Structured plan with 3–4 tasks across business domains. |
| `awaiting_approval` | Pipeline halts at human interrupt | `{"checkpoint": "plan" \| "draft", "thread_id": str, "company_name": str, "data": {...}}` | Signals user action is required. Data contains `research_plan` (for plan) or `report_draft` (for draft). |
| `researcher_started` | Parallel worker dispatched | `{"task_id": str, "domain": str, "queries": list[str]}` | Emitted per domain task as parallel web research begins. |
| `researcher_finished` | Parallel worker completes search & extraction | `{"task_id": str, "domain": str, "confidence": float, "sources_count": int, "top_insight": str, "sources": [{"title": str, "url": str}]}` | Detailed findings per domain, deterministic confidence score (capped at 0.90), and cited URLs. |
| `writer_started` | Findings fan-in; synthesis begins | `{"reason": "initial" \| "revision", "feedback": str \| null}` | Writer node starts aggregating findings and generating the Markdown report. |
| `writer_finished` | Draft generation complete | `{"draft_length": int, "report_draft": str}` | Contains full preliminary Markdown report draft with inline citations `[X]` and References section. |
| `report_ready` | Draft approved and finalized | `{"thread_id": str, "final_report": str}` | Final approved Markdown report ready for display, download, or export. |
| `done` | Execution pass complete | `{"thread_id": str, "status": "awaiting_approval" \| "complete"}` | Terminal event for current HTTP connection stream. |
| `error` | Warning or non-fatal exception | `{"message": str, "type": str}` | Node-level error notice. |

---

## 4. API Request & Response Reference

### 4.1 POST `/analyze`
Initiates a new pipeline run.

**Request:**
```http
POST /analyze HTTP/1.1
Content-Type: application/json

{
  "company_name": "Figma",
  "company_url": "https://figma.com"
}
```

**Response:** `text/event-stream`  
Emits: `session_created` -> `planner_started` -> `plan_ready` -> `awaiting_approval` (checkpoint: "plan") -> `done`.

---

### 4.2 POST `/resume/{thread_id}`
Resumes execution from a pending checkpoint. Automatically detects which checkpoint is pending.

#### Case A: Resuming Checkpoint 1 (Plan Approval)
- **Approve proposed plan:**
  ```json
  { "action": "approve" }
  ```
- **Edit proposed plan:**
  ```json
  {
    "action": "edit",
    "research_plan": [
      {
        "task_id": "task_pricing_01",
        "domain": "pricing_packaging",
        "description": "Analyze Figma pricing tiers and seat costs.",
        "search_queries": ["Figma pricing tiers 2024", "Figma seat cost"],
        "target_questions": ["What are Figma's pricing tiers?"]
      }
    ]
  }
  ```
**Emits:** `researcher_started` (x N) -> `researcher_finished` (x N) -> `writer_started` -> `writer_finished` -> `awaiting_approval` (checkpoint: "draft") -> `done`.

#### Case B: Resuming Checkpoint 2 (Draft Approval)
- **Approve draft:**
  ```json
  { "action": "approve" }
  ```
  **Emits:** `report_ready` -> `done` (`status`: "complete").

- **Request revisions:**
  ```json
  {
    "action": "request_changes",
    "feedback": "Please expand on the enterprise discount structures and security certifications."
  }
  ```
  **Emits:** `writer_started` (`reason`: "revision") -> `writer_finished` -> `awaiting_approval` (checkpoint: "draft") -> `done`.

---

### 4.3 GET `/status/{thread_id}`
Inspects state of any existing thread without consuming an event stream.

**Response:** `application/json`
```json
{
  "thread_id": "session-d10ffa60",
  "company_name": "Figma",
  "company_url": null,
  "status": "awaiting_plan_approval",
  "pending_checkpoint": "plan",
  "next_nodes": ["human_review"],
  "research_plan_count": 4,
  "research_plan": [...],
  "findings_count": 0,
  "has_draft": false,
  "report_draft_length": 0,
  "has_final_report": false,
  "final_report_length": 0
}
```

---

### 4.4 Error Status Codes

- `404 Not Found`: Thread ID does not exist in checkpointer database.
  ```json
  { "detail": "Thread 'non-existent-uuid' not found or has no active checkpoint history." }
  ```
- `400 Bad Request`: Thread ID is already completed and has no pending checkpoints.
  ```json
  { "detail": "Thread 'session-xyz' has already completed and is not awaiting approval." }
  ```
