"""Writer node for CompetitorIQ LangGraph pipeline.

Aggregates grounded researcher findings and generates an executive-ready,
source-grounded Markdown competitive analysis report with inline numeric
citations and a References section. Supports iterative revision driven by
human feedback from the draft review checkpoint.
"""

from __future__ import annotations

import os
from typing import Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas.state_schema import CompetitorIQState, SourceItem


WRITER_SYSTEM_PROMPT = """You are the Senior Intelligence Synthesizer for CompetitorIQ.
Your role is to transform raw competitive research findings into an executive-ready,
strictly grounded Markdown competitive intelligence report for startup founders.

STRICT GROUNDING & CITATION DISCIPLINE:
1. MANDATORY INLINE CITATIONS: Every factual claim, statistic, pricing metric, feature capability,
   customer review sentiment, valuation, and funding detail MUST have an inline numbered citation
   corresponding to the provided source numbers (e.g., "Linear raised $82M at a $1.25B valuation [4]",
   or "Pricing starts at $10/user/month billed annually [1, 2]").
2. ZERO SPECULATION / STRICT EVIDENCE LIMITS: You must ONLY state facts that are explicitly supported
   by the provided findings and sources. If a detail is missing, omit it or explicitly state that it is
   unconfirmed. DO NOT extrapolate, assume, or pull information from your outside training knowledge.
3. COMPREHENSIVE STRATEGIC SYNTHESIS: The synthesis section must provide strategic analysis derived
   from the verified facts—identifying genuine vulnerabilities, founder wedges, and competitive moats.

REQUIRED REPORT STRUCTURE:
# Competitive Intelligence Report: {company_name}

## 1. Executive Summary
High-level overview of the competitor's market position, business model, and strategic posture.
Every factual assertion must include inline citations [X].

## 2. Key Domain Findings
Synthesize the evidence domain by domain (e.g. Pricing & Packaging, Feature Set, Customer Sentiment, News & Funding).
Every paragraph and bullet must be grounded with inline citations [X].

## 3. Strategic Synthesis: Risks & Opportunities
Synthesize actionable founder intelligence derived strictly from the cited facts:
- **Competitor's Core Vulnerabilities**: Exposed flanks, pricing friction, customer backlash, or scaling bottlenecks.
- **Opportunities for Our Startup**: Actionable wedges, pricing arbitrage, underserved customer segments, or unmet needs.
- **Key Threats**: Competitor's structural moats, capital strength, and network effects.

## 4. References
List all cited sources in numerical order matching the inline citations used in the text:
[1] Title: URL
[2] Title: URL
"""


def get_writer_llm() -> Any:
    """Instantiate and configure the Anthropic Chat model for report generation."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is not set or empty. "
            "Please add your Anthropic API key to .env before running the pipeline."
        )

    model_name = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    return ChatAnthropic(
        model=model_name,
        temperature=0.2,
        api_key=api_key,
        max_tokens=4096,
    )


def writer_node(state: CompetitorIQState) -> dict[str, Any]:
    """Execute the Writer node to synthesize findings into a grounded Markdown draft.

    Reads: company_name, findings, report_feedback
    Writes: report_draft
    """
    company_name = state.get("company_name", "Target Company")
    findings = state.get("findings", [])
    report_feedback = state.get("report_feedback")

    # 1. Build a deduplicated, globally indexed source catalog across all findings
    all_sources: list[SourceItem] = []
    source_url_to_idx: dict[str, int] = {}

    for f in findings:
        for s in f.sources:
            if s.url not in source_url_to_idx:
                source_url_to_idx[s.url] = len(all_sources) + 1
                all_sources.append(s)

    # 2. Format findings with explicit source citation numbers
    formatted_finding_blocks: list[str] = []
    for f in findings:
        sources_list: list[str] = []
        for s in f.sources:
            idx = source_url_to_idx[s.url]
            snippet_clean = s.snippet.replace("\n", " ").strip()[:280]
            sources_list.append(f"  [{idx}] {s.title} ({s.url})\n      Excerpt: \"{snippet_clean}\"")

        block = (
            f"### Domain: {f.domain.value} (Task ID: {f.task_id})\n"
            f"- Confidence Score: {f.confidence_score:.2f}\n"
            f"- Key Insights:\n" + "\n".join([f"  * {k}" for k in f.key_insights]) + "\n"
            f"- Detailed Summary:\n  {f.detailed_summary}\n"
            f"- Grounded Sources Available for this Task:\n" + ("\n".join(sources_list) if sources_list else "  (None)")
        )
        formatted_finding_blocks.append(block)

    findings_context = "\n\n".join(formatted_finding_blocks) if formatted_finding_blocks else "No findings recorded."

    # 3. Format complete references catalog
    catalog_lines = [
        f"[{idx}] {s.title}: {s.url}"
        for idx, s in enumerate(all_sources, 1)
    ]
    catalog_str = "\n".join(catalog_lines) if catalog_lines else "(No sources available)"

    # 4. Handle iterative human reviewer feedback if revising previous draft
    feedback_prompt_addon = ""
    if report_feedback:
        feedback_prompt_addon = (
            f"\n\n"
            f"======================================================================\n"
            f"HUMAN REVIEWER FEEDBACK ON PREVIOUS DRAFT:\n"
            f"The human reviewer reviewed the previous report draft and requested the following changes:\n"
            f"\"{report_feedback}\"\n\n"
            f"DIRECTIVE: You MUST revise and expand the report to address this feedback directly.\n"
            f"Significantly deepen and flesh out the requested sections while remaining strictly\n"
            f"grounded in the verified research findings and retaining inline citations.\n"
            f"======================================================================\n"
        )

    user_prompt = (
        f"Synthesize the following research findings into the structured, citation-grounded competitive intelligence report for {company_name}.\n\n"
        f"AVAILABLE GROUNDED FINDINGS:\n"
        f"{findings_context}\n\n"
        f"MASTER SOURCE CATALOG (Use these citation numbers [X] throughout your report):\n"
        f"{catalog_str}"
        f"{feedback_prompt_addon}"
    )

    llm = get_writer_llm()
    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT.format(company_name=company_name)),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)
    report_text = str(response.content)

    return {
        "report_draft": report_text,
    }
