"""Isolation Test for CompetitorIQ Concurrency & Fan-Out/Fan-In State Merging.

Validates that concurrent researcher writes do not encounter race conditions,
drop updates, or duplicate task IDs in a standalone process execution.
Compatible with Phase 3 human approval checkpoint (auto-approved via Command).
"""

from __future__ import annotations

import argparse
import datetime
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

from langgraph.types import Command  # noqa: E402
from app.graph import create_competitor_iq_graph  # noqa: E402
from app.schemas.state_schema import CompetitorIQState  # noqa: E402


def run_isolation_check(company_name: str = "Linear", run_id: str | None = None) -> None:
    """Execute one full graph run and assert concurrency invariants."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f" ISOLATION TEST EXECUTION {f'[{run_id}]' if run_id else ''} - {timestamp} "
    print("=" * 70, flush=True)
    print(header.center(70, "="), flush=True)
    print(f" Target Company : {company_name}", flush=True)
    print(f" Timestamp      : {timestamp}", flush=True)
    print("=" * 70, flush=True)

    thread_id = f"iso-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}
    graph = create_competitor_iq_graph()

    initial_state: CompetitorIQState = {
        "company_name": company_name,
        "company_url": "https://linear.app",
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

    print("\n[STEP 1] Invoking graph up to checkpoint interrupt...", flush=True)
    graph.invoke(initial_state, config=config)

    print("[STEP 2] Resuming graph via Command(resume='approve') to trigger parallel researchers...", flush=True)
    graph.invoke(Command(resume="approve"), config=config)

    print("[STEP 3] Approving draft report via Command(resume='approve')...", flush=True)
    result = graph.invoke(Command(resume="approve"), config=config)

    plan = result.get("research_plan", [])
    findings = result.get("findings", [])
    report = result.get("final_report", "")

    print(f"[STEP 4] Graph execution finished.", flush=True)
    print(f"  * Planned Tasks Count : {len(plan)}", flush=True)
    print(f"  * Planned Task IDs    : {[t.task_id for t in plan]}", flush=True)
    print(f"  * Merged Findings     : {len(findings)}", flush=True)
    print(f"  * Findings Task IDs   : {[f.task_id for f in findings]}", flush=True)
    print(f"  * Report Length       : {len(report)} characters", flush=True)

    print("\n[STEP 5] Evaluating Concurrency & State Reduction Invariants...", flush=True)

    # Invariant 1: Plan is non-empty
    assert len(plan) >= 3, f"ASSERTION FAILED: Plan has fewer than 3 tasks ({len(plan)})."
    print(f"  [PASS] Invariant 1: Planner produced non-empty plan ({len(plan)} tasks).", flush=True)

    # Invariant 2: len(findings) == len(research_plan) every time
    assert len(findings) == len(plan), (
        f"ASSERTION FAILED: Race condition detected! len(findings)={len(findings)} "
        f"does not equal len(research_plan)={len(plan)}."
    )
    print(f"  [PASS] Invariant 2: len(findings) == len(research_plan) ({len(findings)} == {len(plan)}).", flush=True)

    # Invariant 3: No duplicate findings
    finding_task_ids = [f.task_id for f in findings]
    unique_finding_ids = set(finding_task_ids)
    assert len(finding_task_ids) == len(unique_finding_ids), (
        f"ASSERTION FAILED: Duplicate finding task_ids detected: {finding_task_ids}"
    )
    print(f"  [PASS] Invariant 3: Zero duplicate finding task IDs in state.", flush=True)

    # Invariant 4: Exact 1-to-1 bijection between plan task_ids and finding task_ids
    plan_task_ids = {t.task_id for t in plan}
    assert unique_finding_ids == plan_task_ids, (
        f"ASSERTION FAILED: Bijection mismatch! "
        f"Expected: {plan_task_ids}, Got: {unique_finding_ids}, "
        f"Missing: {plan_task_ids - unique_finding_ids}"
    )
    print(f"  [PASS] Invariant 4: Exact 1-to-1 bijection between plan tasks and findings.", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f" >>> RUN {'(' + run_id + ') ' if run_id else ''}PASSED ALL CONCURRENCY INVARIANTS CLEANLY <<<", flush=True)
    print("=" * 70 + "\n", flush=True)


def main() -> None:
    """Parse CLI args and execute a single isolation run."""
    parser = argparse.ArgumentParser(description="CompetitorIQ Concurrency Isolation Test")
    parser.add_argument("-c", "--company", default="Linear", help="Target company")
    parser.add_argument("-r", "--run-id", default=None, help="Identifier for the run")
    args = parser.parse_args()

    try:
        run_isolation_check(company_name=args.company, run_id=args.run_id)
    except Exception as exc:
        print(f"\n[ISOLATION TEST FAILED]: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
