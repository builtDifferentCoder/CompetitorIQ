"""Planner node for CompetitorIQ LangGraph pipeline.

Decomposes a target company name into a structured list of discrete research tasks
using an Anthropic chat model with structured outputs.
"""

from __future__ import annotations

import os
from typing import Any
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.schemas.state_schema import (
    CompetitorIQState,
    ResearchDomain,
    ResearchTask,
)


class ResearchPlanOutput(BaseModel):
    """Wrapper model for structured LLM plan generation."""

    tasks: list[ResearchTask] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="List of 3 to 4 distinct, non-overlapping competitive research tasks.",
    )


PLANNER_SYSTEM_PROMPT = """You are the Lead Strategic Planner for CompetitorIQ, an AI competitive intelligence engine for startup founders.
Your job is to analyze the target company and generate a comprehensive research plan consisting of 3 to 4 discrete, non-overlapping research tasks.

Available research domains:
- pricing_packaging: Tiers, seat costs, discount models, monetization strategies.
- feature_set: Core platform features, technical integrations, limitations.
- customer_sentiment: User reviews, praise patterns, pain points, churn reasons.
- news_funding: Funding rounds, investors, executive hires, corporate milestones.
- positioning_messaging: Target ICP, value propositions, category positioning.

Guidelines:
1. Generate exactly 3 to 4 high-signal tasks across distinct domains.
2. For each task, provide 2-3 specific Tavily search queries tailored to finding verified factual data.
3. Formulate 2-3 key questions the researcher must answer.
4. Use unique descriptive task IDs (e.g., 'task_pricing_01', 'task_features_01').
"""

PLANNER_USER_PROMPT = """Generate a competitive research plan for the following target company:
Company Name: {company_name}
Optional URL: {company_url}
"""


def get_planner_llm() -> Any:
    """Instantiate and configure the Anthropic Chat model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is not set or empty. "
            "Please add your Anthropic API key to .env before running the pipeline."
        )

    model_name = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    return ChatAnthropic(
        model=model_name,
        temperature=0.1,
        api_key=api_key,
        max_tokens=4096,
    )


def planner_node(state: CompetitorIQState) -> dict[str, Any]:
    """Execute the Planner node to generate a structured research plan.

    Reads: company_name, company_url
    Writes: research_plan
    """
    company_name = state.get("company_name")
    if not company_name:
        raise ValueError("Cannot run planner: 'company_name' is missing in graph state.")

    company_url = state.get("company_url") or "Not provided"

    llm = get_planner_llm()
    structured_llm = llm.with_structured_output(ResearchPlanOutput)

    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_SYSTEM_PROMPT),
        ("human", PLANNER_USER_PROMPT),
    ])

    chain = prompt | structured_llm
    plan_output: ResearchPlanOutput = chain.invoke({
        "company_name": company_name,
        "company_url": company_url,
    })

    return {
        "research_plan": plan_output.tasks,
    }
