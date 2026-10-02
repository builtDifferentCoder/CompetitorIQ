"""Step B: Independent OS process resuming graph from SQLite checkpoint using thread_id.

Reconstructs the graph, reconnects to the SqliteSaver checkpointer using the
thread_id passed from the CLI, and invokes Command(resume="approve").
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env")

from langgraph.types import Command  # noqa: E402
from app.graph import create_competitor_iq_graph  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Step B: Resume graph from checkpoint in separate OS process")
    parser.add_argument("thread_id", help="Thread ID from Step A")
    args = parser.parse_args()

    thread_id = args.thread_id
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 70, flush=True)
    print(f" [PROCESS 2] step_b.py - Thread ID: {thread_id}", flush=True)
    print("=" * 70, flush=True)

    print(f"[STEP B] Instantiating graph and connecting to SQLite checkpointer...", flush=True)
    graph = create_competitor_iq_graph()

    # Retrieve existing checkpoint state from SQLite disk
    snapshot = graph.get_state(config)
    print(f"[STEP B] Retrieved snapshot values: {list(snapshot.values.keys())}", flush=True)
    print(f"[STEP B] Retrieved snapshot next:   {snapshot.next}", flush=True)
    print(f"[STEP B] Pending task interrupts:   {[i.value.get('action') for t in snapshot.tasks for i in t.interrupts]}", flush=True)

    if not snapshot.values:
        print("\n[CRITICAL ERROR] Snapshot is EMPTY! No checkpoint state was found for thread_id:", thread_id, flush=True)
        sys.exit(1)

    print(f"\n[STEP B] Resuming graph execution from SQLite checkpoint via Command(resume='approve')...", flush=True)
    try:
        result = graph.invoke(Command(resume="approve"), config=config)
        print("\n[STEP B] Resume succeeded! Graph reached END state.", flush=True)

        final_state = graph.get_state(config)
        findings = final_state.values.get("findings", [])
        report = final_state.values.get("final_report", "")

        print(f"  * Merged findings count: {len(findings)}", flush=True)
        print(f"  * Finding task IDs:      {[f.task_id for f in findings]}", flush=True)
        print(f"  * Final report length:   {len(report)} characters", flush=True)

        print("\n" + "=" * 70, flush=True)
        print(" FINAL REPORT PREVIEW (First 500 chars):", flush=True)
        print("=" * 70, flush=True)
        print(report[:500] + ("..." if len(report) > 500 else ""), flush=True)
        print("=" * 70, flush=True)

    except Exception as exc:
        print(f"\n[STEP B EXECUTION FAILED]: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
