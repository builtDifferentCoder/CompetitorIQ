"""Graph definition and orchestration for CompetitorIQ.

Phase 4 pipeline with Dual Human-in-the-Loop Checkpoints:
START -> planner -> human_review (interrupt 1: plan review)
                 -> [Send fanout to N parallel researchers]
                 -> [Fan-in barrier via operator.add reducer]
                 -> writer
                 -> draft_review (interrupt 2: draft review)
                 -> [conditional: approve -> END | request_changes -> writer]
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    get_checkpoint_metadata,
)
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send
from langchain_core.runnables import RunnableConfig

from app.schemas.state_schema import CompetitorIQState
from app.nodes.planner import planner_node
from app.nodes.human_review import human_review_node
from app.nodes.researcher import researcher_node
from app.nodes.writer import writer_node
from app.nodes.draft_review import draft_review_node

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHECKPOINT_DB = PROJECT_ROOT / "checkpoints.db"


class CompetitorIQSqliteSaver(SqliteSaver):
    """SQLite checkpointer with robust JSON serialization for Pydantic state metadata.

    Standard SqliteSaver uses json.dumps without a default encoder for checkpoint metadata,
    which fails when node writes include Pydantic models (such as ResearchTask and Finding).
    CompetitorIQSqliteSaver ensures all metadata writes serialize reliably.
    """

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"]["checkpoint_ns"]
        type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)

        meta = get_checkpoint_metadata(config, metadata)
        serialized_metadata = json.dumps(
            meta,
            ensure_ascii=False,
            default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o),
        ).encode("utf-8", "ignore")

        with self.cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(config["configurable"]["thread_id"]),
                    checkpoint_ns,
                    checkpoint["id"],
                    config["configurable"].get("checkpoint_id"),
                    type_,
                    serialized_checkpoint,
                    serialized_metadata,
                ),
            )
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }


def get_sqlite_checkpointer(db_path: Path | str | None = None) -> CompetitorIQSqliteSaver:
    """Initialize and return a durable SQLite checkpointer.

    NOTE: Checkpoints ARE persisted to disk via SQLite. WAL mode (Write-Ahead Logging)
    and a busy timeout (5000ms) are explicitly enabled to reduce write-lock contention
    risk under concurrent execution. This provides robust cross-process and cross-request
    state persistence, which is suitable for local development, CLI tooling, and
    single-instance server deployments (such as a single FastAPI/Uvicorn worker).

    FORWARD-LOOKING DEPLOYMENT NOTE:
    While WAL mode mitigates write-lock contention on a single host, SQLite cannot
    synchronize state across distinct physical hosts or distributed container replicas
    with separate filesystems. In a multi-instance production environment, SQLite should
    be replaced with a centralized network-accessible checkpointer such as PostgresSaver
    (backed by managed PostgreSQL, e.g. Supabase, Neon, or Railway Postgres).
    """
    path = db_path or os.getenv("CHECKPOINTS_DB_PATH", str(DEFAULT_CHECKPOINT_DB))
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    saver = CompetitorIQSqliteSaver(conn)
    saver.setup()
    return saver


def fanout_to_researchers(state: CompetitorIQState) -> list[Send]:
    """Fan out: dispatch exactly one Send per ResearchTask.

    CRITICAL SCOPING RULE:
    Each researcher instance receives ONLY its single assigned task and company name.
    It does NOT receive the full research plan. This ensures strict isolation
    and true task-level parallelism.
    """
    tasks = state.get("research_plan", [])
    company_name = state.get("company_name", "")
    return [
        Send("researcher", {"task": task, "company_name": company_name})
        for task in tasks
    ]


def route_draft_approval(state: CompetitorIQState) -> str:
    """Conditional router following draft_review checkpoint.

    If report_approved is True: routes to END.
    If report_approved is False (request_changes): routes back to writer for regeneration.
    """
    if state.get("report_approved", False):
        return END
    return "writer"


def create_competitor_iq_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    db_path: Path | str | None = None,
) -> CompiledStateGraph:
    """Build and compile the Phase 4 CompetitorIQ StateGraph.

    Control flow:
    1. planner: Generates structured research_plan (list[ResearchTask])
    2. human_review (Interrupt 1): Triggers interrupt() for human inspection/edit of research_plan.
    3. fanout_to_researchers: Dispatches N parallel researcher nodes via Send API for the approved plan.
    4. researcher (parallel): Gathers web search data and outputs single Finding.
    5. Fan-in barrier: LangGraph merges all worker findings into state['findings'].
    6. writer: Synthesizes aggregated findings into grounded report_draft.
    7. draft_review (Interrupt 2): Triggers interrupt() for human review of report_draft.
    8. route_draft_approval: Routes to END if approved, or loops back to writer if revisions requested.
    """
    if checkpointer is None:
        checkpointer = get_sqlite_checkpointer(db_path=db_path)

    builder = StateGraph(CompetitorIQState)

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("writer", writer_node)
    builder.add_node("draft_review", draft_review_node)

    # Wire edges
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "human_review")
    # Dynamic fanout conditional edge from human_review to parallel researcher nodes
    builder.add_conditional_edges("human_review", fanout_to_researchers, ["researcher"])
    # Fan-in synchronization barrier: waits for all parallel researchers to finish
    builder.add_edge("researcher", "writer")
    # Writer passes synthesized draft to draft_review checkpoint
    builder.add_edge("writer", "draft_review")
    # Conditional edge: approve -> END; request_changes -> writer
    builder.add_conditional_edges(
        "draft_review",
        route_draft_approval,
        ["writer", END],
    )

    return builder.compile(checkpointer=checkpointer)
