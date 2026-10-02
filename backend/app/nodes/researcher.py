"""Real researcher node for CompetitorIQ LangGraph pipeline.

Executes Tavily web search queries for a single assigned ResearchTask,
extracts evidence, and uses an Anthropic LLM call with strict grounding
to produce a structured Finding.
"""

from __future__ import annotations

import os
from typing import Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas.state_schema import (
    Finding,
    ResearchTask,
    SourceItem,
)
from app.tools.search import TavilySearchTool, SearchResultItem


RESEARCHER_SYSTEM_PROMPT = """You are an objective, rigorous competitive intelligence researcher for CompetitorIQ.
Your role is to analyze retrieved web search excerpts and extract a structured Finding for the assigned research task.

STRICT GROUNDING & BREVITY RULES:
1. Base your key insights, detailed summary, and raw data points EXCLUSIVELY on the provided web search excerpts.
2. DO NOT use outside knowledge, prior training assumptions, or unverified claims.
3. Keep `key_insights` to 3-4 bullet points and `detailed_summary` to 1-2 focused, factual paragraphs.
4. If a target question cannot be answered from the provided excerpts, explicitly state that it is unconfirmed or not found in the search results.
5. Extract only genuine URLs and titles from the provided search results for the `sources` field.
"""

RESEARCHER_USER_PROMPT = """Analyze the following web search results and extract a structured finding for this research task:

Company: {company_name}
Task ID: {task_id}
Domain: {domain}
Task Description: {description}

Target Questions:
{target_questions}

Web Search Results:
{search_excerpts}
"""


def get_researcher_llm() -> Any:
    """Instantiate and configure the Anthropic Chat model."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    model_name = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    return ChatAnthropic(
        model=model_name,
        temperature=0.0,
        api_key=api_key,
        max_tokens=4096,
    )


def compute_confidence_score(num_sources: int) -> float:
    """Compute confidence score deterministically based on unique corroborating source count.

    NOTE ON CEILING (0.90):
    We deliberately cap the maximum confidence at 0.90 (never 0.95 or 1.0).
    An automated web search pipeline without human verification should never claim
    near-certainty, as web content may still contain marketing bias, stale data, or PR claims.
    This ceiling is a deliberate engineering constraint to ensure honesty in intelligence reporting.
    """
    if num_sources == 0:
        return 0.0
    elif num_sources == 1:
        return 0.35
    elif num_sources == 2:
        return 0.55
    elif 3 <= num_sources <= 4:
        return 0.70
    else:  # 5+
        return min(0.90, round(0.70 + (num_sources - 4) * 0.04, 2))


def researcher_node(state: dict[str, Any]) -> dict[str, list[Finding]]:
    """Execute research on a single ResearchTask.

    Scoped strictly to state['task'] and state['company_name'] via LangGraph Send API.
    Does NOT receive the full research plan.

    Reads: task (ResearchTask), company_name (str)
    Writes: findings (Annotated[list[Finding], operator.add])
    """
    raw_task = state.get("task")
    company_name = state.get("company_name", "Target Company")

    if not raw_task:
        raise ValueError("Researcher received state without an assigned 'task'.")

    # Ensure task is a ResearchTask instance
    if isinstance(raw_task, dict):
        task = ResearchTask.model_validate(raw_task)
    else:
        task = raw_task

    # 1. Execute Tavily search queries attached to this task
    search_tool = TavilySearchTool()
    collected_results: list[SearchResultItem] = []
    search_error: str | None = None

    # Run up to 3 queries attached to this task
    queries_to_run = task.search_queries[:3] if task.search_queries else [
        f"{company_name} {task.domain.value} competitive analysis"
    ]

    for query in queries_to_run:
        try:
            results = search_tool.search(query=query, max_results=3)
            collected_results.extend(results)
        except Exception as exc:
            search_error = str(exc)
            # Continue to next query rather than crashing
            continue

    # Deduplicate results by URL
    seen_urls: set[str] = set()
    unique_results: list[SearchResultItem] = []
    for r in collected_results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            unique_results.append(r)

    # 2. Handle zero search results or complete search failure
    if not unique_results:
        failure_finding = Finding(
            task_id=task.task_id,
            domain=task.domain,
            key_insights=[
                f"Web search yielded zero usable results for task '{task.task_id}' ({task.domain.value}).",
                "No public citations could be verified for this competitive dimension.",
            ],
            detailed_summary=(
                f"External search via Tavily returned no verified results for {company_name} "
                f"in domain '{task.domain.value}'. Queries attempted: {', '.join(queries_to_run)}. "
                f"Failure reason: {search_error or 'Zero search results returned by search provider.'}"
            ),
            raw_data_points={
                "search_status": "failed",
                "queries_attempted": queries_to_run,
                "error": search_error or "zero_results",
            },
            sources=[],
            confidence_score=0.0,
        )
        return {"findings": [failure_finding]}

    # 3. Format search excerpts for the LLM
    excerpt_blocks: list[str] = []
    for idx, item in enumerate(unique_results, 1):
        excerpt_blocks.append(
            f"[{idx}] Source Title: {item.title}\n"
            f"    URL: {item.url}\n"
            f"    Content: {item.snippet[:600]}"
        )
    search_excerpts = "\n\n".join(excerpt_blocks)

    questions_formatted = "\n".join(
        [f"- {q}" for q in task.target_questions]
    ) if task.target_questions else "- What are the key competitive metrics for this domain?"

    # 4. Invoke LLM with structured output to extract grounded Finding
    llm = get_researcher_llm()
    structured_llm = llm.with_structured_output(Finding)

    user_content = RESEARCHER_USER_PROMPT.format(
        company_name=company_name,
        task_id=task.task_id,
        domain=task.domain.value,
        description=task.description,
        target_questions=questions_formatted,
        search_excerpts=search_excerpts,
    )

    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    # Compute confidence deterministically from verified source count
    num_sources = len(unique_results)
    computed_confidence = compute_confidence_score(num_sources)

    try:
        finding: Finding = structured_llm.invoke(messages)
        # Ensure task_id, domain, and deterministic confidence are strictly enforced
        finding.task_id = task.task_id
        finding.domain = task.domain
        finding.confidence_score = computed_confidence
        finding.raw_data_points["sources_retrieved"] = num_sources
        finding.raw_data_points["source_urls"] = [r.url for r in unique_results]

        # Ensure all unique source URLs returned by Tavily are retained
        existing_urls = {s.url for s in finding.sources}
        for r in unique_results:
            if r.url not in existing_urls:
                finding.sources.append(
                    SourceItem(url=r.url, title=r.title, snippet=r.snippet[:400])
                )
    except Exception as exc:
        # Graceful fallback on LLM structured parse error
        finding = Finding(
            task_id=task.task_id,
            domain=task.domain,
            key_insights=[f"Extraction error processing search results: {exc}"],
            detailed_summary=(
                f"Search results were retrieved for {task.task_id}, but LLM structured extraction failed: {exc}."
            ),
            raw_data_points={"error": str(exc)},
            sources=[
                SourceItem(url=r.url, title=r.title, snippet=r.snippet[:200])
                for r in unique_results[:3]
            ],
            confidence_score=computed_confidence,
        )

    # 5. Return single Finding in a list for reducer concatenation
    return {"findings": [finding]}
