# CompetitorIQ — System Architecture

## 1. Product Description

CompetitorIQ is an automated competitive intelligence engine designed for startup founders, product strategists, and venture operators who need deep, objective market intelligence without spending days manually scouring pricing pages, changelogs, review forums, and financial disclosures. By accepting a single target company name (and optional URL), CompetitorIQ autonomously plans a comprehensive research agenda across five core business dimensions, solicits human approval or refinement of the research plan to prevent wasted API calls and irrelevant search paths, dispatches specialized research agents in parallel to gather ground-truth web evidence via Tavily, and synthesizes findings into an executive-ready Markdown dossier complete with actionable opportunities and defensive vulnerabilities.

---

## 2. Agent Responsibility Statements

Each agent in the CompetitorIQ pipeline adheres to strict single-responsibility boundaries. If any role cannot be definitively stated in a single sentence, it is flagged as underspecified below:

- **Planner / Orchestrator**:
  Decomposes the target company's competitive landscape into a validated, non-overlapping list of discrete research tasks equipped with targeted search queries and evaluation criteria.
- **Pricing & Packaging Researcher**:
  Extracts and verifies the target company's current pricing tiers, seat minimums, billing cadences, enterprise packaging, and discount mechanisms from public web data.
- **Feature Set & Tech Stack Researcher**:
  Catalogs the target company's core platform capabilities, architectural integrations, proprietary technologies, and notable product limitations from technical documentation and release notes.
- **Customer Sentiment Researcher**:
  Aggregates authentic user perceptions, frequent feature complaints, praise patterns, and churn triggers by surveying public review aggregators and community discussions.
- **News, Funding & Corporate Milestones Researcher**:
  Compiles the company's capitalization history, executive leadership changes, strategic partnerships, and material legal or regulatory events from financial databases and press releases.
- **Positioning & Messaging Researcher**:
  Deconstructs the target company's value proposition, ideal customer profile (ICP) targeting, category framing, and core marketing narratives across its primary digital touchpoints.
- **Writer / Synthesizer**:
  Correlates, cross-validates, and synthesizes all researcher outputs into a cohesive Markdown intelligence report that highlights emergent risks, strategic weaknesses, and competitive whitespace.

*(Status: All 7 agent roles are strictly specified in single crisp sentences; none are underspecified).*

---

## 3. Graph Architecture & Workflow Diagram

CompetitorIQ is implemented as a directed acyclic LangGraph pipeline featuring deterministic routing, human-in-the-loop checkpointing, and dynamic map-reduce parallelism via LangGraph's `Send` API.

```mermaid
flowchart TD
    %% Styling
    classDef startEnd fill:#1e293b,stroke:#0f172a,stroke-width:2px,color:#fff
    classDef agent fill:#0284c7,stroke:#0369a1,stroke-width:2px,color:#fff
    classDef interrupt fill:#d97706,stroke:#b45309,stroke-width:2px,color:#fff
    classDef barrier fill:#475569,stroke:#334155,stroke-width:2px,color:#fff
    classDef decision fill:#6366f1,stroke:#4f46e5,stroke-width:2px,color:#fff

    START([START: User inputs company_name]) :::startEnd
    NodePlanner["planner<br/>(Generates Research Plan)"] :::agent
    CheckpointHuman{"human_review<br/>[INTERRUPT: Approval Checkpoint]"} :::interrupt
    DecisionRoute{"plan_approved == true?"} :::decision
    
    subgraph ParallelFanOut ["Dynamic Parallel Execution (Send API)"]
        direction TB
        NodeR1["researcher: Pricing & Packaging"] :::agent
        NodeR2["researcher: Feature Set"] :::agent
        NodeR3["researcher: Customer Sentiment"] :::agent
        NodeR4["researcher: News & Funding"] :::agent
        NodeR5["researcher: Positioning & Messaging"] :::agent
    end

    SyncBarrier["Fan-In Barrier<br/>(operator.add Reducer Merges Findings)"] :::barrier
    NodeWriter["writer<br/>(Report Synthesis & Strategic Analysis)"] :::agent
    END([END: Final Report Rendered]) :::startEnd

    %% Transitions
    START --> NodePlanner
    NodePlanner --> CheckpointHuman
    CheckpointHuman --> DecisionRoute

    %% Re-plan or proceed
    DecisionRoute -- "No (Edit / Feedback)" --> NodePlanner
    DecisionRoute -- "Yes (Approved)" --> NodeR1 & NodeR2 & NodeR3 & NodeR4 & NodeR5

    %% Fan-in
    NodeR1 --> SyncBarrier
    NodeR2 --> SyncBarrier
    NodeR3 --> SyncBarrier
    NodeR4 --> SyncBarrier
    NodeR5 --> SyncBarrier

    SyncBarrier --> NodeWriter
    NodeWriter --> END
```

### Execution Flow Step-by-Step

1. **Initialization (`START`)**: Graph state is seeded with `company_name` (and optional `company_url`).
2. **Planning (`planner`)**: The Planner LLM outputs a structured `list[ResearchTask]`, stored in `state["research_plan"]`.
3. **Interrupt Boundary (`human_review`)**: The graph pauses execution before dispatching external web calls using LangGraph's native checkpoint/interrupt mechanism. The user can:
   - Accept the plan as-is (`plan_approved = True`).
   - Edit, delete, or add specific `ResearchTask` items directly in state.
   - Reject the plan with corrective text feedback (`user_feedback`), routing back to `planner` for regeneration.
4. **Dynamic Fan-Out (`Send` API)**: A conditional routing edge inspects `state["research_plan"]` and yields an array of `Send("researcher", task)` objects. This instantiates 3–5 parallel researcher nodes, each bound to exactly one `ResearchTask`.
5. **Concurrent Web Research**: Each researcher node conducts search queries via Tavily, extracts evidence, and returns an atomic state update: `{"findings": [Finding(...)]}`.
6. **Fan-In Barrier & State Reduction**: LangGraph halts the writer until all `Send` instances terminate. State updates merge into `state["findings"]` using the `operator.add` reducer, eliminating race conditions.
7. **Synthesis (`writer`)**: The Writer agent reads the aggregated findings and company metadata to produce a structured, high-signal Markdown document containing an executive summary, comparative matrices, and strategic risks/opportunities.
8. **Completion (`END`)**: Report is finalized and made available to the API/streaming interface.

---

## 4. Architectural Rationale: Why This Pattern?

CompetitorIQ intentionally adopts a **Supervisor / Planner Pattern with Deterministic Graph Routing** (treating the plan as static data routed over explicit graph edges) rather than a **Decentralized Swarm / Autonomous Agent-to-Agent Handoff Pattern**.

### Tradeoff Analysis

| Metric | Supervisor Pattern with Deterministic Routing (Chosen) | Decentralized Agent Swarm (Rejected) |
| :--- | :--- | :--- |
| **Control & Predictability** | **High**: Graph path is fixed; LLM controls payload data, not execution topology. | **Low**: Agents dynamically decide who speaks next; risk of infinite chatter loops. |
| **Human Checkpointing** | **Trivial & First-Class**: Clean, declarative pause boundary right after plan generation. | **Fragile**: Difficult to interrupt when handoff transitions emerge ad-hoc at runtime. |
| **Cost & Token Bounds** | **Deterministic**: Fixed `N` researcher runs; worst-case token spend is bounded and budgeted. | **Unbounded**: Autonomous agents can call tools and spawn sub-agents recursively. |
| **Inspectability & Debugging** | **High**: Complete state replayability with time-travel via LangGraph checkpoints. | **Low**: Distributed state across disparate message threads makes tracing bugs difficult. |
| **Task Agility** | **Moderate**: Researchers cannot autonomously redefine the scope outside their assigned task. | **High**: Agents can pivot on the fly without a centralized coordinator. |

### Rationale

In competitive intelligence, unconstrained agent swarms are notorious for hallucinating recursive search threads, burning Tavily search credits, and meandering into tangential corporate trivia.

By enforcing **Plan as Data**:
1. The Planner agent acts purely as an architect, turning a high-level goal into an explicit, inspectable data structure (`list[ResearchTask]`).
2. Graph edges—not LLM whim—control execution flow and concurrency.
3. The human-in-the-loop checkpoint sits cleanly between the cheap step (generating the plan, ~1,000 tokens) and the expensive step (3–5 parallel web searches and document scrapes).
4. The system is trivial to debug: any failed finding or invalid query maps directly back to a single `task_id` in the checkpointed state.

---

## 5. Phase 5: FastAPI Backend & SSE Streaming Layer

The graph is exposed to the frontend via a FastAPI HTTP API located in [`backend/app/server.py`](file:///c:/Users/Hamza/Downloads/multi-agent-research/backend/app/server.py) and [`backend/app/main.py`](file:///c:/Users/Hamza/Downloads/multi-agent-research/backend/app/main.py).

- **Decoupled Execution & Lifecycle Isolation**: Client HTTP connection lifecycle is decoupled from LangGraph execution. Graph execution runs in a daemon thread pushing events to an internal queue; client drops do not abort execution or corrupt state.
- **Checkpointer**: Persistent SQLite checkpointing (`CompetitorIQSqliteSaver`) across processes and HTTP requests.
- **Curated SSE Contract**: See [`docs/SSE_API_SPEC.md`](file:///c:/Users/Hamza/Downloads/multi-agent-research/docs/SSE_API_SPEC.md) for full event types, payloads, and state transitions.

