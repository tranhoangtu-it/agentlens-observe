"""Basic AgentLens SDK usage.

Demonstrates:
- agentlens.configure()        — point SDK at the server
- @agentlens.trace()           — wrap an agent function
- agentlens.span() context     — create tool_call / llm_call child spans
- SpanContext.set_output()     — record what the span produced
- SpanContext.set_cost()       — attach token cost to an LLM call
- agentlens.log()              — add structured log messages inside a span
"""
import time

import agentlens

# ---------------------------------------------------------------------------
# Configuration — point the SDK at the local AgentLens server.
# ---------------------------------------------------------------------------
agentlens.configure(server_url="http://localhost:3000")


# ---------------------------------------------------------------------------
# Simulated tool / LLM helpers (no real API calls required).
# ---------------------------------------------------------------------------

def _fake_web_search(query: str) -> str:
    """Simulate a web search tool returning a snippet."""
    time.sleep(0.6)
    return (
        f"Search results for '{query}': "
        "Found 3 papers — 'Attention Is All You Need' (2017), "
        "'BERT: Pre-training of Deep Bidirectional Transformers' (2018), "
        "'GPT-4 Technical Report' (2023)."
    )


def _fake_database_query(table: str) -> str:
    """Simulate a database lookup."""
    time.sleep(0.4)
    return f"SELECT * FROM {table} WHERE status='active' → 42 rows returned."


def _fake_llm_summarize(context: str) -> str:
    """Simulate an LLM summarization call."""
    time.sleep(1.0)
    return (
        "Summary: The retrieved papers cover transformer architectures, "
        "pre-trained language models, and the latest GPT-4 capabilities. "
        "Key themes: attention mechanisms, transfer learning, scale."
    )


# ---------------------------------------------------------------------------
# Agent function — decorated with @agentlens.trace so every call becomes
# a trace visible in the dashboard.
# ---------------------------------------------------------------------------

@agentlens.trace(name="ResearchAgent")
def run_research_agent(query: str) -> str:
    """A research agent that searches, queries a DB, then summarizes findings."""

    # --- Tool call: web search -----------------------------------------------
    with agentlens.span("web_search", "tool_call") as s:
        agentlens.log("Starting web search", query=query)
        search_result = _fake_web_search(query)
        s.set_output(search_result)
        print(f"  [web_search] done — {len(search_result)} chars")

    # --- Tool call: database query -------------------------------------------
    with agentlens.span("database_query", "tool_call") as s:
        agentlens.log("Querying internal knowledge base", table="research_papers")
        db_result = _fake_database_query("research_papers")
        s.set_output(db_result)
        print(f"  [database_query] done — {db_result}")

    # --- LLM call: summarize findings ----------------------------------------
    context = f"{search_result}\n{db_result}"
    with agentlens.span("summarize", "llm_call") as s:
        agentlens.log("Calling LLM to synthesize results", model="gpt-4o")
        summary = _fake_llm_summarize(context)
        s.set_output(summary)
        # Record token usage — SDK auto-calculates USD from the model price table.
        s.set_cost("gpt-4o", input_tokens=820, output_tokens=150)
        print(f"  [summarize] done — cost tracked (gpt-4o, 820+150 tokens)")

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query = "Latest AI research papers on transformer architectures"
    print(f"\nRunning ResearchAgent for: '{query}'")
    print("-" * 55)

    result = run_research_agent(query)

    print("-" * 55)
    print(f"Result: {result[:120]}...")
    print("\nTrace sent to AgentLens — open http://localhost:3000 to inspect.")
