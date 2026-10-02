"""Phase 3 Verification: Human-in-the-Loop Interrupt & Resume Tests.

Tests:
1. Verify interrupt mechanism: Step A halts at human_review checkpoint without blocking.
2. Verify approve path: Step B resumes from checkpoint with 'approve', completing full pipeline.
3. Verify edit path: Step B resumes with an edited plan (1 task removed), confirming:
   - len(findings) == len(edited_plan) < len(original_plan)
   - Every finding task_id matches the edited plan task IDs
   - The removed task never executed and is not present in findings
"""

from __future__ import annotations

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


def test_interrupt_edit_path(company_name: str = "Linear") -> None:
    """Explicitly verify that modifying the plan at interrupt affects downstream fan-out."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 70, flush=True)
    print(" PHASE 3 VERIFICATION: EDIT PATH (TASK REMOVAL TEST) ".center(70, "="), flush=True)
    print(f" Target Company : {company_name}", flush=True)
    print(f" Timestamp      : {timestamp}", flush=True)
    print("=" * 70 + "\n", flush=True)

    graph = create_competitor_iq_graph()
    thread_id = f"test-edit-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: CompetitorIQState = {
        "company_name": company_name,
        "company_url": "https://linear.app",
        "research_plan": [],
        "plan_approved": False,
        "user_feedback": None,
        "findings": [],
        "final_report": None,
        "errors": [],
    }

    # ---------------------------------------------------------
    # STEP A: Initial invocation up to interrupt
    # ---------------------------------------------------------
    print(f"[STEP A] Starting initial invocation (thread_id: {thread_id})...", flush=True)
    step_a_result = graph.invoke(initial_state, config=config)

    # Inspect checkpointed state at interrupt
    state_at_interrupt = graph.get_state(config)
    print(f"  * Graph paused. Next nodes waiting: {state_at_interrupt.next}", flush=True)
    assert "human_review" in state_at_interrupt.next, (
        f"ASSERTION FAILED: Expected 'human_review' in next nodes, got {state_at_interrupt.next}"
    )

    original_plan = state_at_interrupt.values.get("research_plan", [])
    original_count = len(original_plan)
    print(f"  * Planner generated {original_count} tasks:", flush=True)
    for idx, t in enumerate(original_plan, 1):
        print(f"    {idx}. [{t.domain.value}] {t.task_id}: {t.description}", flush=True)

    assert original_count >= 3, f"ASSERTION FAILED: Expected at least 3 tasks, got {original_count}"

    # ---------------------------------------------------------
    # EDIT THE PLAN: Remove exactly one task
    # ---------------------------------------------------------
    removed_task = original_plan[-1]
    edited_plan = original_plan[:-1]
    edited_count = len(edited_plan)
    print(f"\n[HUMAN EDIT] Removing 1 task from plan:", flush=True)
    print(f"  - REMOVED: [{removed_task.domain.value}] {removed_task.task_id}: {removed_task.description}", flush=True)
    print(f"  - REMAINING TASKS ({edited_count}): {[t.task_id for t in edited_plan]}", flush=True)

    # ---------------------------------------------------------
    # STEP B: Resume invocation with edited plan
    # ---------------------------------------------------------
    print(f"\n[STEP B] Resuming graph via Command(resume={{'research_plan': edited_plan}})...", flush=True)
    resume_cmd = Command(resume={"research_plan": edited_plan})
    final_output = graph.invoke(resume_cmd, config=config)

    final_state = graph.get_state(config)
    final_findings = final_state.values.get("findings", [])
    final_plan = final_state.values.get("research_plan", [])

    # Step C: Phase 4 draft review approval checkpoint
    draft_at_checkpoint = final_state.values.get("report_draft", "")
    assert len(draft_at_checkpoint) > 100, "ASSERTION FAILED: report_draft is empty or too short."
    print(f"  [PASS] Step B produced report_draft ({len(draft_at_checkpoint)} chars), paused at draft_review.", flush=True)

    print("\n[STEP C] Approving draft report via Command(resume='approve')...", flush=True)
    graph.invoke(Command(resume="approve"), config=config)
    end_state = graph.get_state(config)
    final_report = end_state.values.get("final_report", "")

    # Assertions
    # 1. Findings count matches edited plan count, NOT original plan count
    assert len(final_findings) == edited_count, (
        f"ASSERTION FAILED: Expected {edited_count} findings, but got {len(final_findings)}! "
        f"Original count was {original_count}."
    )
    print(f"\n  [PASS] Assertion 1: len(findings) == len(edited_plan) ({len(final_findings)} == {edited_count} != {original_count})", flush=True)

    # 2. Removed task is NOT in findings
    finding_task_ids = {f.task_id for f in final_findings}
    assert removed_task.task_id not in finding_task_ids, (
        f"ASSERTION FAILED: Removed task '{removed_task.task_id}' was found in findings!"
    )
    print(f"  [PASS] Assertion 2: Removed task '{removed_task.task_id}' was NOT executed by any researcher.", flush=True)

    # 3. All remaining tasks have exactly one finding
    expected_ids = {t.task_id for t in edited_plan}
    assert finding_task_ids == expected_ids, (
        f"ASSERTION FAILED: Task IDs mismatch! Expected: {expected_ids}, Got: {finding_task_ids}"
    )
    print(f"  [PASS] Assertion 3: Exact 1-to-1 match between edited tasks and worker findings.", flush=True)

    # 4. Final report generated successfully
    assert len(final_report) > 100, "ASSERTION FAILED: Final report is empty or too short."
    assert final_report == draft_at_checkpoint, "ASSERTION FAILED: final_report does not match approved draft!"
    print(f"  [PASS] Assertion 4: Writer successfully synthesized report for edited tasks ({len(final_report)} chars).", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(" >>> EDIT PATH TEST PASSED ALL ASSERTIONS CLEANLY <<< ".center(70, "="), flush=True)
    print("=" * 70 + "\n", flush=True)


if __name__ == "__main__":
    test_interrupt_edit_path()
