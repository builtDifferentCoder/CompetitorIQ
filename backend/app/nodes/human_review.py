"""Human review node for CompetitorIQ.

Surfaces the Planner's generated research plan to the human reviewer via
LangGraph's interrupt() mechanism, allowing review, approval, or plan edits
prior to parallel researcher fan-out.
"""

from __future__ import annotations

from typing import Any
from langgraph.types import interrupt
from app.schemas.state_schema import CompetitorIQState, ResearchTask


def human_review_node(state: CompetitorIQState) -> dict[str, Any]:
    """Human review node positioned between planner and researcher fan-out.

    Surfaces research_plan for human review and unwinds execution via interrupt().
    Upon resume via Command(resume=...), receives either an approval or an updated research plan.

    Interrupt payload:
    - action: "review_plan"
    - company_name: target company name
    - research_plan: list of task dicts (serialized ResearchTask objects)

    Resume payload supported formats:
    - "approve" or {"action": "approve"}: approves existing plan as-is
    - {"research_plan": [...]}: approves with modified/edited list of ResearchTask objects or dicts
    - list of ResearchTask / dicts: directly replaces research_plan with modified tasks
    """
    current_plan = state.get("research_plan", [])
    serialized_plan = [
        task.model_dump() if hasattr(task, "model_dump") else dict(task)
        for task in current_plan
    ]

    # Pause graph execution and surface plan to caller
    resume_payload = interrupt({
        "action": "review_plan",
        "company_name": state.get("company_name", ""),
        "research_plan": serialized_plan,
    })

    # Process resume action
    if isinstance(resume_payload, dict):
        if "research_plan" in resume_payload:
            raw_tasks = resume_payload["research_plan"]
            validated_tasks = [
                ResearchTask.model_validate(t) if isinstance(t, dict) else t
                for t in raw_tasks
            ]
            return {"research_plan": validated_tasks, "plan_approved": True}
        return {"plan_approved": True}
    elif isinstance(resume_payload, list):
        validated_tasks = [
            ResearchTask.model_validate(t) if isinstance(t, dict) else t
            for t in resume_payload
        ]
        return {"research_plan": validated_tasks, "plan_approved": True}
    elif resume_payload in ("approve", "approved", True):
        return {"plan_approved": True}

    # Default fallback: keep existing plan approved
    return {"plan_approved": True}
