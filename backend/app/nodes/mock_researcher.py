"""Mock researcher node for CompetitorIQ Phase 1 skeleton.

Generates synthetic, deterministic findings for each task in research_plan without
calling any external search APIs. Isolates graph control flow and state passing.
"""

from __future__ import annotations

from typing import Any
from app.schemas.state_schema import (
    CompetitorIQState,
    Finding,
    SourceItem,
)


def mock_researcher_node(state: CompetitorIQState) -> dict[str, Any]:
    """Execute the mock researcher node.

    Iterates through each task in research_plan and produces a placeholder
    Finding object conforming to the Finding schema.

    Reads: research_plan, company_name
    Writes: findings
    """
    research_plan = state.get("research_plan", [])
    company_name = state.get("company_name", "Target Company")

    mock_findings: list[Finding] = []

    for task in research_plan:
        mock_finding = Finding(
            task_id=task.task_id,
            domain=task.domain,
            key_insights=[
                f"MOCK INSIGHT: Placeholder finding for {task.domain.value} on {company_name}.",
                f"MOCK INSIGHT: Simulated competitive metric for task '{task.task_id}'.",
            ],
            detailed_summary=(
                f"MOCK FINDING for task: {task.task_id} ({task.domain.value}). "
                f"Simulated investigation of {task.description}. "
                "This is deliberate synthetic placeholder content designed to validate graph "
                "wiring and state reduction in Phase 1 before integrating Tavily search in Phase 2."
            ),
            raw_data_points={
                "mock_status": "simulated_success",
                "task_id": task.task_id,
                "queries_simulated": task.search_queries,
            },
            sources=[
                SourceItem(
                    url=f"https://mock-source.example.com/{task.domain.value}",
                    title=f"Mock Intelligence Source for {task.domain.value.title()}",
                    snippet=(
                        f"MOCK CITATION: Simulated evidence verifying insights for "
                        f"{task.task_id} relating to {company_name}."
                    ),
                )
            ],
            confidence_score=1.0,
        )
        mock_findings.append(mock_finding)

    return {
        "findings": mock_findings,
    }
