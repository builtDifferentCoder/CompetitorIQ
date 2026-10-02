"""Draft review node for CompetitorIQ LangGraph pipeline.

Surfaces the Writer's synthesized report draft to the human reviewer via
LangGraph's interrupt() mechanism, allowing review, approval, or change requests
prior to finalizing the intelligence report.
"""

from __future__ import annotations

from typing import Any
from langgraph.types import interrupt
from app.schemas.state_schema import CompetitorIQState


def draft_review_node(state: CompetitorIQState) -> dict[str, Any]:
    """Human review node positioned after the Writer for draft report approval.

    Surfaces report_draft for human review and unwinds graph execution via interrupt().
    Upon resume via Command(resume=...), receives either an approval or change request.

    Interrupt payload:
    - action: "review_draft"
    - company_name: target company name
    - report_draft: full synthesized markdown draft

    Resume payload supported formats:
    - "approve" or {"action": "approve"}:
      Sets report_approved=True, final_report=report_draft, report_feedback=None.
    - {"action": "request_changes", "feedback": "focus on pricing risks"}:
      Sets report_approved=False, report_feedback="...", routing back to writer.
    - text string other than "approve":
      Treated as feedback note for change request.
    """
    report_draft = state.get("report_draft", "")

    resume_payload = interrupt({
        "action": "review_draft",
        "company_name": state.get("company_name", ""),
        "report_draft": report_draft,
    })

    # Process resume action
    if isinstance(resume_payload, dict):
        action = resume_payload.get("action", "")
        if action == "request_changes" or "feedback" in resume_payload:
            feedback_text = resume_payload.get("feedback", "").strip() or "Please revise the report draft."
            return {
                "report_approved": False,
                "report_feedback": feedback_text,
                "final_report": None,
            }
        # Default dict approval
        return {
            "report_approved": True,
            "final_report": report_draft,
            "report_feedback": None,
        }
    elif isinstance(resume_payload, str):
        if resume_payload.lower() in ("approve", "approved", "yes", "y"):
            return {
                "report_approved": True,
                "final_report": report_draft,
                "report_feedback": None,
            }
        else:
            # Non-approve string is treated as feedback note requesting revisions
            return {
                "report_approved": False,
                "report_feedback": resume_payload.strip(),
                "final_report": None,
            }

    # Fallback approval
    return {
        "report_approved": True,
        "final_report": report_draft,
        "report_feedback": None,
    }
