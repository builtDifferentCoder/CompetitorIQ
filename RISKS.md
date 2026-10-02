# CompetitorIQ — Technical Risk Analysis & Early Validation Spikes

As a full-stack engineer tackling your first multi-agent LangGraph system, two technical bottlenecks represent the highest failure risk. Both stem from subtle concurrency and streaming mechanics in distributed state machines rather than standard CRUD or REST logic.

Below is an analysis of each risk and the **earliest, cheapest validation spike** to prove the pattern works before writing production agent logic.

---

## Risk 1: Concurrent State Writes from Parallel Researchers (`Send` API Fan-Out)

### What Makes This Hard
When running 3–5 researchers in parallel using LangGraph's dynamic `Send` API, multiple worker nodes execute concurrently on separate event loops or threads. In a single super-step, all active researchers attempt to write their output back to the root graph state under the same state key: `findings`.

In standard Python or naive LangGraph state configurations:
1. **Conflicting Write Exceptions**: Without an explicit reducer annotation, LangGraph's engine detects concurrent state mutations to the same key and raises an `InvalidUpdateError` (or silently permits a race condition where the last researcher to finish completely overwrites the findings of the earlier researchers).
2. **Partial Failures & Zombie State**: If 4 researchers succeed and 1 researcher fails (e.g. rate-limited Tavily search or network timeout), the graph must gracefully capture partial findings without crashing the entire graph run or hanging the fan-in synchronization barrier.
3. **Data Shape Asymmetry**: The researcher node input is an individual `ResearchTask`, but the output must be a delta list `{"findings": [Finding(...)]}` that conforms to the parent state's reducer signature.

### The Earliest, Cheapest Validation Spike (Estimated Time: 15–20 min)
Before writing any prompts, LLM invocations, or Tavily API integrations:

1. **Create an isolated scratch test**: Build a 30-line standalone Python script using a dummy `StateGraph`.
2. **Define dummy tasks & state**:
   ```python
   import operator, random, asyncio
   from typing import Annotated
   from typing_extensions import TypedDict
   from langgraph.graph import StateGraph, START, END
   from langgraph.types import Send

   class SpikeState(TypedDict):
       tasks: list[str]
       findings: Annotated[list[str], operator.add]

   def planner(state: SpikeState):
       return {"tasks": ["pricing", "features", "sentiment"]}

   def route_researchers(state: SpikeState):
       return [Send("researcher", {"task": t}) for t in state["tasks"]]

   async def researcher(state_input: dict):
       # Simulate asynchronous, out-of-order execution with random sleep
       delay = random.uniform(0.1, 0.4)
       await asyncio.sleep(delay)
       return {"findings": [f"Result for {state_input['task']} after {delay:.2f}s"]}

   def writer(state: SpikeState):
       return {} # Fan-in consumer
   ```
3. **Run 50 iterations**: Execute `app.ainvoke({"tasks": [], "findings": []})` in a loop.
4. **Pass Criteria**:
   - `len(state["findings"]) == 3` on every single run.
   - Zero `InvalidUpdateError` exceptions.
   - Verifies that `operator.add` monotonically merges out-of-order writes cleanly.

---

## Risk 2: Streaming Graph Events to Frontend Without Leaking LangGraph Internal Noise

### What Makes This Hard
In LangGraph, invoking `.astream_events(version="v2")` streams every internal lifecycle event triggered by the engine. A single graph execution can emit hundreds of raw event payloads:
- Internal LangChain AST events (`on_chain_start`, `on_chain_end`, `on_tool_start`, `on_tool_end`)
- Intermediate token chunks generated during the Planner's private scratchpad or tool-calling steps
- Raw system prompts, internal metadata, and execution IDs
- Subgraph orchestration events from concurrent workers

If you pipe raw LangGraph event streams directly into a Next.js frontend:
1. **Network Bloat**: Hundreds of unnecessary JSON blobs overwhelm the Server-Sent Events (SSE) socket.
2. **Security & Prompt Leakage**: Internal system prompts, Tavily API request payloads, and chain trace identifiers leak to client browser devtools.
3. **Frontend UI Breakdown**: The frontend cannot easily differentiate between a temporary researcher token chunk and the final report Markdown stream, resulting in flashing, scrambled, or broken UI components.

### The Earliest, Cheapest Validation Spike (Estimated Time: 25–30 min)
Before building the Next.js UI or full FastAPI backend:

1. **Define a strict Server-Sent Event (SSE) Contract**:
   Create a domain-level event schema wrapper:
   ```python
   # Only 3 event types ever reach the client:
   # 1. {"event": "node_status", "data": {"node": "planner", "status": "running"}}
   # 2. {"event": "plan_ready", "data": {"plan": [...]}}
   # 3. {"event": "report_chunk", "data": {"delta": "..."}}
   ```
2. **Build a 40-line minimal FastAPI endpoint**:
   Use `EventSourceResponse` (from `sse-starlette`) with an async generator filter:
   ```python
   async def event_filter(graph, input_data):
       async for event in graph.astream_events(input_data, version="v2"):
           kind = event["event"]
           metadata = event.get("metadata", {})
           node_name = metadata.get("langgraph_node")

           # Filter rule: Only stream tokens if they originate explicitly from the writer node
           if kind == "on_chat_model_stream" and node_name == "writer":
               chunk = event["data"]["chunk"].content
               if chunk:
                   yield {"event": "report_chunk", "data": chunk}

           # Filter rule: Node lifecycle changes
           elif kind == "on_chain_start" and node_name in ["planner", "researcher", "writer"]:
               yield {"event": "node_status", "data": {"node": node_name, "status": "started"}}
   ```
3. **Verify with `curl` or Postman**:
   Run:
   ```bash
   curl -N http://localhost:8000/stream-test
   ```
4. **Pass Criteria**:
   - The terminal output shows clean, legible text without raw LangGraph JSON noise.
   - The client receives only business-relevant status updates and final report markdown tokens.
   - No prompt leakage or Tavily raw tool payload is visible in the stream.
