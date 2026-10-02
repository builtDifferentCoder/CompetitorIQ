"""Skeleton test for CompetitorIQ Phase 1.

Asserts the three core structural invariants of the skeleton graph:
1. research_plan is non-empty after planner runs
2. findings has the same length as research_plan after researcher runs
3. final_report is non-empty at the end
"""

from __future__ import annotations

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

from app.graph import create_competitor_iq_graph  # noqa: E402
from app.schemas.state_schema import CompetitorIQState  # noqa: E402


def test_pipeline_skeleton() -> None:
    """Run the graph and assert all Phase 1 structural invariants."""
    print("\n>>> Running CompetitorIQ Phase 1 Skeleton Verification Test...")

    graph = create_competitor_iq_graph()

    initial_state: CompetitorIQState = {
        "company_name": "Linear",
        "company_url": "https://linear.app",
        "research_plan": [],
        "plan_approved": False,
        "user_feedback": None,
        "findings": [],
        "final_report": None,
        "errors": [],
    }

    state_snapshot: dict = dict(initial_state)

    for step_output in graph.stream(initial_state, stream_mode="updates"):
        for node_name, updates in step_output.items():
            if node_name == "planner":
                state_snapshot["research_plan"] = updates.get("research_plan", [])
                # Invariant 1: research_plan is non-empty after planner runs
                assert len(state_snapshot["research_plan"]) > 0, (
                    "Assertion Failed: research_plan is empty after planner runs!"
                )
                print(
                    f"[ASSERT 1 PASS] Planner produced {len(state_snapshot['research_plan'])} tasks."
                )

            elif node_name == "researcher":
                findings = updates.get("findings", [])
                state_snapshot.setdefault("findings", []).extend(findings)
                # Invariant 2: findings has same length as research_plan after researcher runs
                assert len(state_snapshot["findings"]) == len(state_snapshot["research_plan"]), (
                    f"Assertion Failed: findings length ({len(state_snapshot['findings'])}) "
                    f"does not match research_plan length ({len(state_snapshot['research_plan'])})!"
                )
                print(
                    f"[ASSERT 2 PASS] Researcher produced {len(state_snapshot['findings'])} findings matching tasks."
                )

            elif node_name == "writer":
                state_snapshot["final_report"] = updates.get("final_report")
                # Invariant 3: final_report is non-empty at the end
                assert (
                    state_snapshot["final_report"] is not None
                    and len(state_snapshot["final_report"].strip()) > 0
                ), "Assertion Failed: final_report is empty after writer runs!"
                print(
                    f"[ASSERT 3 PASS] Writer generated final_report ({len(state_snapshot['final_report'])} chars)."
                )

    print("\n>>> ALL SKELETON INVARIANTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    try:
        test_pipeline_skeleton()
    except Exception as exc:
        print(f"\n[TEST FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
