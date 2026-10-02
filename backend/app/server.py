"""CompetitorIQ FastAPI Backend & Server-Sent Events (SSE) Streaming API.

================================================================================
EVENT VOCABULARY & API CONTRACT (Phase 5 Contract for Phase 6 Frontend)
================================================================================
All SSE messages follow the standard W3C EventSource protocol:
  event: <event_name>\n
  data: <json_string>\n\n

Event Types & Payloads:
--------------------------------------------------------------------------------
1. session_created:
   Emitted immediately upon graph initialization.
   Payload: { "thread_id": str, "company_name": str, "company_url": str | null }

2. planner_started:
   Emitted when Planner begins decomposing company intelligence goals.
   Payload: { "company_name": str }

3. plan_ready:
   Emitted when Planner completes the structured research plan.
   Payload: { "thread_id": str, "research_plan": list[ResearchTaskDict] }

4. awaiting_approval:
   Emitted when pipeline halts at a human checkpoint (Interrupt 1 or Interrupt 2).
   Payload: {
     "checkpoint": "plan" | "draft",
     "thread_id": str,
     "company_name": str,
     "data": {
       "research_plan"?: list[ResearchTaskDict],   # When checkpoint == "plan"
       "report_draft"?: str                       # When checkpoint == "draft"
     }
   }

5. researcher_started:
   Emitted when an individual parallel researcher is dispatched via Send API.
   Payload: { "task_id": str, "domain": str, "queries": list[str] }

6. researcher_finished:
   Emitted when an individual researcher completes web search & fact extraction.
   Payload: {
     "task_id": str,
     "domain": str,
     "confidence": float,
     "sources_count": int,
     "top_insight": str,
     "sources": list[{ "title": str, "url": str }]
   }

7. writer_started:
   Emitted when all findings fan-in and Writer starts synthesis (or revision).
   Payload: { "reason": "initial" | "revision", "feedback"?: str }

8. writer_finished:
   Emitted when Writer completes report draft generation.
   Payload: { "draft_length": int, "report_draft": str }

9. report_ready:
   Emitted when human approves draft and final Markdown report is finalized.
   Payload: { "thread_id": str, "final_report": str }

10. done:
    Terminal event indicating that the current execution pass has completed.
    Payload: { "thread_id": str, "status": "awaiting_approval" | "complete" }

11. error:
    Emitted on non-fatal node warnings or fatal pipeline exceptions.
    Payload: { "message": str, "type": str }
================================================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure backend directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env")

from app.graph import create_competitor_iq_graph  # noqa: E402
from app.schemas.state_schema import CompetitorIQState, ResearchTask  # noqa: E402
from langgraph.types import Command  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("competitor_iq_server")

# Instantiate shared graph with durable SQLite checkpointer
graph = create_competitor_iq_graph()

app = FastAPI(
    title="CompetitorIQ API",
    description="Multi-Agent Competitive Intelligence Engine with Human-in-the-Loop Checkpoints",
    version="1.0.0",
)

# CORS Configuration: reads ALLOWED_ORIGINS from environment (comma-separated), with local fallbacks
raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_allowed_origins.strip():
    allowed_origins = [o.strip() for o in raw_allowed_origins.split(",") if o.strip()]
    # Ensure standard local origins are available for hybrid testing
    for local_url in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        if local_url not in allowed_origins:
            allowed_origins.append(local_url)
    allow_all = "*" in allowed_origins
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]
    allow_all = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)



# =============================================================================
# Request / Response Schemas
# =============================================================================

class AnalyzeRequest(BaseModel):
    company_name: str = Field(..., example="Figma", description="Target company name to analyze.")
    company_url: Optional[str] = Field(None, example="https://figma.com", description="Optional company URL.")


class ResumeRequest(BaseModel):
    action: str = Field(
        "approve",
        example="approve",
        description="Decision action: 'approve', 'edit', or 'request_changes'.",
    )
    research_plan: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Modified research plan (applicable when action='edit' at plan checkpoint).",
    )
    feedback: Optional[str] = Field(
        None,
        example="Focus more on enterprise pricing and security tiers.",
        description="Revision feedback note (applicable when action='request_changes' at draft checkpoint).",
    )


# =============================================================================
# Execution Session & Decoupled Streaming Worker
# =============================================================================

class ExecutionSession:
    """Manages an active decoupled execution run.

    Decouples graph execution lifetime from the client HTTP connection.
    If a client drops the SSE stream, graph execution continues to the next
    checkpoint and persists state in SQLite.
    """

    def __init__(self, thread_id: str, loop: asyncio.AbstractEventLoop):
        self.thread_id = thread_id
        self.loop = loop
        self.queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
        self.is_closed = False

    def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """Thread-safe enqueueing of an SSE event."""
        if not self.is_closed:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, (event_name, payload))

    def close(self) -> None:
        """Signal end of stream."""
        if not self.is_closed:
            self.is_closed = True
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)


def run_graph_sync_worker(
    session: ExecutionSession,
    input_or_command: Any,
    config: dict[str, Any],
) -> None:
    """Synchronous worker running graph execution in background thread."""
    thread_id = session.thread_id
    try:
        for step_output in graph.stream(input_or_command, config=config, stream_mode="updates"):
            for node_name, updates in step_output.items():
                if node_name == "__interrupt__":
                    # Execution reached an interrupt checkpoint
                    snapshot = graph.get_state(config)
                    next_nodes = snapshot.next
                    company_name = snapshot.values.get("company_name", "")

                    if "human_review" in next_nodes:
                        plan = snapshot.values.get("research_plan", [])
                        session.emit(
                            "awaiting_approval",
                            {
                                "checkpoint": "plan",
                                "thread_id": thread_id,
                                "company_name": company_name,
                                "data": {
                                    "research_plan": [
                                        t.model_dump() if hasattr(t, "model_dump") else t
                                        for t in plan
                                    ]
                                },
                            },
                        )
                    elif "draft_review" in next_nodes:
                        draft = snapshot.values.get("report_draft", "")
                        session.emit(
                            "awaiting_approval",
                            {
                                "checkpoint": "draft",
                                "thread_id": thread_id,
                                "company_name": company_name,
                                "data": {
                                    "report_draft": draft,
                                },
                            },
                        )

                    session.emit(
                        "done",
                        {
                            "thread_id": thread_id,
                            "status": "awaiting_approval",
                        },
                    )
                    return

                elif node_name == "planner":
                    plan = updates.get("research_plan", [])
                    session.emit(
                        "plan_ready",
                        {
                            "thread_id": thread_id,
                            "research_plan": [
                                t.model_dump() if hasattr(t, "model_dump") else t
                                for t in plan
                            ],
                        },
                    )

                elif node_name == "human_review":
                    # Dispatched fan-out: emit researcher_started events
                    snapshot = graph.get_state(config)
                    active_plan = snapshot.values.get("research_plan", [])
                    for task in active_plan:
                        t_id = task.task_id if hasattr(task, "task_id") else task.get("task_id")
                        dom = (
                            task.domain.value
                            if hasattr(task, "domain") and hasattr(task.domain, "value")
                            else str(task.get("domain", ""))
                        )
                        queries = (
                            task.search_queries
                            if hasattr(task, "search_queries")
                            else task.get("search_queries", [])
                        )
                        session.emit(
                            "researcher_started",
                            {
                                "task_id": t_id,
                                "domain": dom,
                                "queries": queries,
                            },
                        )

                elif node_name == "researcher":
                    findings = updates.get("findings", [])
                    for f in findings:
                        dom = f.domain.value if hasattr(f.domain, "value") else str(f.domain)
                        sources_count = f.raw_data_points.get("sources_retrieved", len(f.sources))
                        session.emit(
                            "researcher_finished",
                            {
                                "task_id": f.task_id,
                                "domain": dom,
                                "confidence": f.confidence_score,
                                "sources_count": sources_count,
                                "top_insight": f.key_insights[0] if f.key_insights else "",
                                "sources": [
                                    {"title": s.title, "url": s.url} for s in f.sources
                                ],
                            },
                        )

                elif node_name == "writer":
                    draft = updates.get("report_draft", "")
                    session.emit(
                        "writer_finished",
                        {
                            "draft_length": len(draft),
                            "report_draft": draft,
                        },
                    )

                elif node_name == "draft_review":
                    if updates.get("report_approved"):
                        final_rep = updates.get("final_report", "")
                        session.emit(
                            "report_ready",
                            {
                                "thread_id": thread_id,
                                "final_report": final_rep,
                            },
                        )
                    elif updates.get("report_feedback"):
                        session.emit(
                            "writer_started",
                            {
                                "reason": "revision",
                                "feedback": updates.get("report_feedback"),
                            },
                        )

        # Check if pipeline completed to END
        final_snapshot = graph.get_state(config)
        if not final_snapshot.next:
            report = final_snapshot.values.get("final_report", "")
            if report:
                session.emit("report_ready", {"thread_id": thread_id, "final_report": report})
            session.emit("done", {"thread_id": thread_id, "status": "complete"})

    except Exception as exc:
        logger.exception("Pipeline execution error for thread %s", thread_id)
        session.emit(
            "error",
            {
                "message": str(exc),
                "type": type(exc).__name__,
            },
        )
    finally:
        session.close()


async def stream_sse_generator(session: ExecutionSession):
    """Asynchronous generator yielding formatted SSE text chunks."""
    try:
        while True:
            item = await session.queue.get()
            if item is None:
                break
            event_name, payload = item
            yield f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        # Client disconnected mid-stream
        logger.info(
            "Client disconnected SSE stream for thread %s. Background worker continues executing.",
            session.thread_id,
        )


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    """Initiates competitive intelligence pipeline for target company.

    Streams curated SSE events until the first checkpoint (Plan Review).
    Returns thread_id in the initial session_created event.
    """
    thread_id = f"session-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: CompetitorIQState = {
        "company_name": req.company_name,
        "company_url": req.company_url,
        "research_plan": [],
        "plan_approved": False,
        "user_feedback": None,
        "findings": [],
        "report_draft": None,
        "report_approved": False,
        "report_feedback": None,
        "final_report": None,
        "errors": [],
    }

    loop = asyncio.get_running_loop()
    session = ExecutionSession(thread_id=thread_id, loop=loop)

    # Emit initial handshake event with thread_id
    session.emit(
        "session_created",
        {
            "thread_id": thread_id,
            "company_name": req.company_name,
            "company_url": req.company_url,
        },
    )
    session.emit("planner_started", {"company_name": req.company_name})

    # Launch graph worker in background thread (decoupled from HTTP connection)
    worker_thread = threading.Thread(
        target=run_graph_sync_worker,
        args=(session, initial_state, config),
        daemon=True,
    )
    worker_thread.start()

    return StreamingResponse(
        stream_sse_generator(session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/resume/{thread_id}")
async def resume_endpoint(thread_id: str, req: ResumeRequest):
    """Resumes graph from pending checkpoint (Plan Review or Draft Review).

    Inspects checkpointed state to determine pending checkpoint and routes
    payload accordingly. Streams events until next checkpoint or pipeline completion.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = graph.get_state(config)

    # 1. Validate thread existence
    if not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found or has no active checkpoint history.",
        )

    # 2. Validate pending interrupt status
    next_nodes = state_snapshot.next
    if not next_nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Thread '{thread_id}' has already completed and is not awaiting approval.",
        )

    # 3. Determine pending checkpoint & construct resume Command
    resume_payload: Any
    if "human_review" in next_nodes:
        # Checkpoint 1: Plan Review
        if req.action.lower() in ("edit", "modify") and req.research_plan:
            resume_payload = {"research_plan": req.research_plan}
        else:
            resume_payload = "approve"

    elif "draft_review" in next_nodes:
        # Checkpoint 2: Draft Review
        if req.action.lower() in ("request_changes", "revision") or req.feedback:
            feedback_note = req.feedback or "Please expand and refine the report."
            resume_payload = {"action": "request_changes", "feedback": feedback_note}
        else:
            resume_payload = "approve"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Thread '{thread_id}' is paused at unhandled node: {next_nodes}",
        )

    resume_command = Command(resume=resume_payload)

    loop = asyncio.get_running_loop()
    session = ExecutionSession(thread_id=thread_id, loop=loop)

    if "draft_review" in next_nodes and resume_payload != "approve":
        session.emit("writer_started", {"reason": "revision", "feedback": req.feedback})

    # Launch graph resume in background thread
    worker_thread = threading.Thread(
        target=run_graph_sync_worker,
        args=(session, resume_command, config),
        daemon=True,
    )
    worker_thread.start()

    return StreamingResponse(
        stream_sse_generator(session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/status/{thread_id}")
async def status_endpoint(thread_id: str):
    """Retrieves current execution state snapshot for reconnection or debugging."""
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = graph.get_state(config)

    if not state_snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found.",
        )

    values = state_snapshot.values
    next_nodes = state_snapshot.next

    status_str = "completed"
    pending_cp = None
    if "human_review" in next_nodes:
        status_str = "awaiting_plan_approval"
        pending_cp = "plan"
    elif "draft_review" in next_nodes:
        status_str = "awaiting_draft_approval"
        pending_cp = "draft"
    elif next_nodes:
        status_str = "in_progress"

    plan = values.get("research_plan", [])
    findings = values.get("findings", [])

    return {
        "thread_id": thread_id,
        "company_name": values.get("company_name", ""),
        "company_url": values.get("company_url"),
        "status": status_str,
        "pending_checkpoint": pending_cp,
        "next_nodes": list(next_nodes),
        "research_plan_count": len(plan),
        "research_plan": [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in plan
        ],
        "findings_count": len(findings),
        "has_draft": bool(values.get("report_draft")),
        "report_draft_length": len(values.get("report_draft", "") or ""),
        "has_final_report": bool(values.get("final_report")),
        "final_report_length": len(values.get("final_report", "") or ""),
    }


@app.get("/health")
async def health_endpoint():
    """Health check endpoint."""
    return {"status": "healthy", "service": "CompetitorIQ Backend"}
