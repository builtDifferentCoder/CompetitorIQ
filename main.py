"""CLI entry point for CompetitorIQ (Phase 4).

Executes the LangGraph multi-agent pipeline with dual human-in-the-loop checkpoints:
- Checkpoint 1: Plan approval / editing prior to parallel researcher fan-out.
- Checkpoint 2: Draft approval / revision requests after writer synthesis.
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

# Ensure backend directory is in sys.path
root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Load environment variables (.env in root and backend)
load_dotenv(root_dir / ".env")
load_dotenv(backend_dir / ".env")

from langgraph.types import Command  # noqa: E402
from app.graph import create_competitor_iq_graph  # noqa: E402
from app.schemas.state_schema import CompetitorIQState, ResearchTask  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CompetitorIQ — AI Competitive Intelligence Pipeline (Phase 4 CLI)"
    )
    parser.add_argument(
        "-c",
        "--company",
        type=str,
        default=None,
        help="Target company name to analyze.",
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        default=None,
        help="Optional company URL.",
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default=None,
        help="Optional thread ID for checkpointer state.",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Automatically approve both the plan and the draft report without interactive prompts.",
    )
    parser.add_argument(
        "--delete-task",
        type=int,
        default=None,
        help="Non-interactive: 1-based index of task to delete before resuming.",
    )
    parser.add_argument(
        "--draft-feedback",
        type=str,
        default=None,
        help="Non-interactive: Feedback note to request changes on the draft before auto-approving revised draft.",
    )
    return parser.parse_args()


def print_banner(company_name: str, thread_id: str) -> None:
    """Print an informative CLI banner."""
    print("=" * 70, flush=True)
    print(f" CompetitorIQ — Competitive Intelligence Pipeline (Phase 4)", flush=True)
    print(f" Target Company : {company_name}", flush=True)
    print(f" Thread ID      : {thread_id}", flush=True)
    print(" Pipeline Flow  : START -> planner -> [INTERRUPT 1: human_review]", flush=True)
    print("                  -> [RESUME: Send fanout to parallel researchers]", flush=True)
    print("                  -> [Fan-in state merge] -> writer", flush=True)
    print("                  -> [INTERRUPT 2: draft_review]", flush=True)
    print("                  -> [Approve -> END | Request Changes -> writer]", flush=True)
    print("=" * 70 + "\n", flush=True)


def display_plan(tasks: list[ResearchTask]) -> None:
    """Print the structured research plan with numbered indices."""
    print("\n" + "-" * 70, flush=True)
    print(" PROPOSED RESEARCH PLAN FOR HUMAN REVIEW", flush=True)
    print("-" * 70, flush=True)
    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}] Task ID    : {task.task_id}", flush=True)
        print(f"    Domain     : {task.domain.value}", flush=True)
        print(f"    Directive  : {task.description}", flush=True)
        if task.search_queries:
            print(f"    Queries    : {', '.join(task.search_queries)}", flush=True)
        if task.target_questions:
            print(f"    Questions  : {', '.join(task.target_questions)}", flush=True)
    print("-" * 70 + "\n", flush=True)


def run_pipeline(
    company_name: str,
    company_url: str | None = None,
    thread_id: str | None = None,
    auto_approve: bool = False,
    delete_task_idx: int | None = None,
    draft_feedback: str | None = None,
) -> dict:
    """Execute the Phase 4 pipeline with dual human checkpoints."""
    if not thread_id:
        thread_id = f"session-{uuid.uuid4().hex[:8]}"

    print_banner(company_name, thread_id)

    graph = create_competitor_iq_graph()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: CompetitorIQState = {
        "company_name": company_name,
        "company_url": company_url,
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

    # =========================================================================
    # STEP 1: INITIAL INVOCATION -> INTERRUPT 1 (Plan Review)
    # =========================================================================
    print("=" * 70, flush=True)
    print(f" [STEP 1: INITIAL INVOCATION] Starting graph execution (Thread: {thread_id})", flush=True)
    print("=" * 70 + "\n", flush=True)

    for step_output in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, updates in step_output.items():
            if node_name == "__interrupt__":
                print("\n>>> [CHECKPOINT 1 REACHED] Execution paused at human_review interrupt. <<<", flush=True)
                continue

            print(f"--- [TRANSITION] Node Completed: '{node_name.upper()}' ---", flush=True)
            if node_name == "planner":
                plan = updates.get("research_plan", [])
                print(f"  * Planner produced {len(plan)} structured research tasks.", flush=True)

    state_at_interrupt1 = graph.get_state(config)
    assert "human_review" in state_at_interrupt1.next, "Expected graph to pause at human_review."

    current_plan: list[ResearchTask] = list(state_at_interrupt1.values.get("research_plan", []))
    display_plan(current_plan)

    # Human decision for Plan
    plan_resume_payload: dict | str
    if auto_approve:
        print("[HUMAN DECISION 1] Auto-approve flag set. Approving plan as-is.", flush=True)
        plan_resume_payload = "approve"
    elif delete_task_idx is not None:
        idx = delete_task_idx - 1
        if 0 <= idx < len(current_plan):
            removed = current_plan.pop(idx)
            print(f"[HUMAN DECISION 1] Removed Task [{delete_task_idx}]: {removed.task_id} ({removed.domain.value})", flush=True)
            print(f"Remaining active tasks ({len(current_plan)}): {[t.task_id for t in current_plan]}", flush=True)
            plan_resume_payload = {"research_plan": current_plan}
        else:
            print(f"[WARNING] Invalid delete-task index {delete_task_idx}. Approving as-is.", flush=True)
            plan_resume_payload = "approve"
    else:
        print("Human Review Options (Plan):", flush=True)
        print("  [A] Approve plan as-is and proceed to web research", flush=True)
        print("  [D <#>] Delete a task by number (e.g. 'D 2')", flush=True)
        print("  [Q] Abort execution\n", flush=True)

        while True:
            try:
                choice = input("Enter decision ([A] / [D #] / [Q]): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExecution aborted by user.", flush=True)
                sys.exit(0)

            if not choice or choice.lower() in ("a", "approve", "yes", "y"):
                plan_resume_payload = "approve"
                print("\n[DECISION] Plan approved as-is.", flush=True)
                break
            elif choice.lower() in ("q", "quit", "exit"):
                print("\nExecution cancelled.", flush=True)
                return state_at_interrupt1.values
            elif choice.lower().startswith("d"):
                parts = choice.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    del_num = int(parts[1])
                    del_idx = del_num - 1
                    if 0 <= del_idx < len(current_plan):
                        removed = current_plan.pop(del_idx)
                        print(f"\n[DECISION] Removed Task [{del_num}]: {removed.task_id} ({removed.domain.value})", flush=True)
                        print(f"Remaining tasks ({len(current_plan)}): {[t.task_id for t in current_plan]}", flush=True)
                        plan_resume_payload = {"research_plan": current_plan}
                        break
                    else:
                        print(f"Invalid task number. Must be between 1 and {len(current_plan)}.", flush=True)
                else:
                    print("Usage to delete: D <task_number>, e.g. 'D 2'", flush=True)
            else:
                print("Type 'A' to approve, 'D <#>' to delete, or 'Q' to quit.", flush=True)

    # =========================================================================
    # STEP 2: RESUME PLAN -> RESEARCHERS -> WRITER -> INTERRUPT 2 (Draft Review)
    # =========================================================================
    print("\n" + "=" * 70, flush=True)
    print(f" [STEP 2: RESEARCH & DRAFT SYNTHESIS] Resuming graph from Checkpoint 1", flush=True)
    print("=" * 70 + "\n", flush=True)

    resume_cmd = Command(resume=plan_resume_payload)
    for step_output in graph.stream(resume_cmd, config=config, stream_mode="updates"):
        for node_name, updates in step_output.items():
            if node_name == "__interrupt__":
                print("\n>>> [CHECKPOINT 2 REACHED] Execution paused at draft_review interrupt. <<<", flush=True)
                continue

            if node_name == "human_review":
                approved_plan = updates.get("research_plan", current_plan)
                print(f"--- [TRANSITION] Plan Confirmed ({len(approved_plan)} tasks) ---", flush=True)
                print(f"  [FAN-OUT] Spawning {len(approved_plan)} parallel researchers via Send API...\n", flush=True)

            elif node_name == "researcher":
                findings = updates.get("findings", [])
                for f in findings:
                    sources_count = f.raw_data_points.get("sources_retrieved", len(f.sources))
                    print(
                        f"  [PARALLEL RESEARCHER ARRIVED] Task: {f.task_id} ({f.domain.value})\n"
                        f"    - Grounded sources retained: {sources_count}\n"
                        f"    - Deterministic confidence: {f.confidence_score:.2f}\n"
                        f"    - Top Insight: {f.key_insights[0] if f.key_insights else 'N/A'}",
                        flush=True,
                    )

            elif node_name == "writer":
                draft = updates.get("report_draft", "")
                print(f"\n--- [TRANSITION] Node Completed: 'WRITER' ---", flush=True)
                print(f"  * Synthesized citation-grounded draft ({len(draft)} characters).", flush=True)

    # =========================================================================
    # STEP 3: DRAFT REVIEW & REVISION LOOP (Interrupt 2)
    # =========================================================================
    iteration = 1
    feedback_to_apply = draft_feedback

    while True:
        state_at_interrupt2 = graph.get_state(config)
        next_nodes = state_at_interrupt2.next

        # If graph reached END, we are done
        if not next_nodes or END in next_nodes:
            break

        assert "draft_review" in next_nodes, f"Expected 'draft_review' in next nodes, got {next_nodes}"

        draft_content = state_at_interrupt2.values.get("report_draft", "")
        print("\n" + "=" * 70, flush=True)
        print(f" REPORT DRAFT FOR HUMAN REVIEW (Iteration {iteration})", flush=True)
        print("=" * 70, flush=True)
        print(draft_content, flush=True)
        print("=" * 70 + "\n", flush=True)

        draft_resume_payload: dict | str

        if feedback_to_apply:
            print(f"[HUMAN DECISION 2] Automated feedback provided: \"{feedback_to_apply}\"", flush=True)
            print("[ACTION] Requesting changes from writer node...\n", flush=True)
            draft_resume_payload = {"action": "request_changes", "feedback": feedback_to_apply}
            feedback_to_apply = None  # Clear so next iteration approves
        elif auto_approve:
            print("[HUMAN DECISION 2] Auto-approve flag set. Approving draft report as final.", flush=True)
            draft_resume_payload = "approve"
        else:
            print("Draft Review Options:", flush=True)
            print("  [A] Approve draft and finalize report", flush=True)
            print("  [R] Request changes with a feedback note", flush=True)
            print("  [Q] Abort execution\n", flush=True)

            try:
                choice = input("Enter decision ([A] / [R] / [Q]): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExecution aborted by user.", flush=True)
                sys.exit(0)

            if not choice or choice.lower() in ("a", "approve", "yes", "y"):
                draft_resume_payload = "approve"
            elif choice.lower() in ("q", "quit", "exit"):
                print("\nExecution cancelled.", flush=True)
                return state_at_interrupt2.values
            elif choice.lower().startswith("r"):
                try:
                    note = input("Enter feedback note for the Writer: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\nExecution aborted.", flush=True)
                    sys.exit(0)
                if not note:
                    note = "Please expand and provide more strategic detail."
                draft_resume_payload = {"action": "request_changes", "feedback": note}
            else:
                print("Defaulting to approve.", flush=True)
                draft_resume_payload = "approve"

        # Resume from draft review
        print(f"\n[RESUME INVOCATION] Resuming from draft review checkpoint...", flush=True)
        resume_cmd = Command(resume=draft_resume_payload)
        for step_output in graph.stream(resume_cmd, config=config, stream_mode="updates"):
            for node_name, updates in step_output.items():
                if node_name == "__interrupt__":
                    print("\n>>> [CHECKPOINT 2 REACHED AGAIN] Execution paused for revised draft review. <<<", flush=True)
                    continue

                if node_name == "writer":
                    revised = updates.get("report_draft", "")
                    print(f"--- [TRANSITION] Writer Regenerated Draft ({len(revised)} chars) ---", flush=True)
                    print(f"  * Incorporated reviewer feedback.", flush=True)

        iteration += 1

    final_state = graph.get_state(config)
    report = final_state.values.get("final_report", "")

    print("\n" + "=" * 70, flush=True)
    print(" FINAL APPROVED REPORT", flush=True)
    print("=" * 70 + "\n", flush=True)
    print(report if report else "No final report generated.", flush=True)
    print("\n" + "=" * 70, flush=True)

    return final_state.values


def main() -> None:
    """CLI execution entrypoint."""
    args = parse_args()
    company_name = args.company
    if not company_name:
        try:
            company_name = input("Enter target company name (e.g. Stripe, Linear, Notion): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExecution aborted by user.", flush=True)
            sys.exit(0)

    if not company_name:
        print("Error: Target company name is required.", flush=True)
        sys.exit(1)

    try:
        run_pipeline(
            company_name=company_name,
            company_url=args.url,
            thread_id=args.thread_id,
            auto_approve=args.approve,
            delete_task_idx=args.delete_task,
            draft_feedback=args.draft_feedback,
        )
    except Exception as exc:
        print(f"\n[FATAL ERROR] Pipeline execution failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
