"""Step A: Independent OS process running graph up to human_review interrupt.

Runs the planner, hits the interrupt checkpoint, prints the plan, and
immediately terminates the OS process.
"""

from __future__ import annotations

import argparse
import sys
import uuid
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

from app.graph import create_competitor_iq_graph  # noqa: E402
from app.schemas.state_schema import CompetitorIQState  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Step A: Run to interrupt and exit")
    parser.add_argument("-c", "--company", default="Linear", help="Target company")
    parser.add_argument("-t", "--thread-id", default=None, help="Thread ID")
    args = parser.parse_args()

    thread_id = args.thread_id or f"test-proc-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}

    print("=" * 70, flush=True)
    print(f" [PROCESS 1] step_a.py (PID: {Path().resolve()}) - Thread: {thread_id}", flush=True)
    print("=" * 70, flush=True)

    graph = create_competitor_iq_graph()

    initial_state: CompetitorIQState = {
        "company_name": args.company,
        "company_url": None,
        "research_plan": [],
        "plan_approved": False,
        "user_feedback": None,
        "findings": [],
        "final_report": None,
        "errors": [],
    }

    print(f"[STEP A] Invoking graph for '{args.company}' until interrupt...", flush=True)
    graph.invoke(initial_state, config=config)

    # Inspect checkpointed state
    snapshot = graph.get_state(config)
    print(f"[STEP A] Graph paused. Next nodes: {snapshot.next}", flush=True)

    plan = snapshot.values.get("research_plan", [])
    print(f"[STEP A] Surfaced Research Plan ({len(plan)} tasks):", flush=True)
    for idx, t in enumerate(plan, 1):
        print(f"  {idx}. [{t.domain.value}] {t.task_id}: {t.description}", flush=True)

    print("\n[STEP A] Exiting process cleanly now. Nothing left running in memory.", flush=True)
    print(f"[STEP A] To resume in a new process, run:\n    python step_b.py {thread_id}", flush=True)
    print("=" * 70, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
