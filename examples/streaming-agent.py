"""Real-time streaming demo.

Demonstrates:
- agentlens.configure(streaming=True)   — send spans as they complete
- Spans appear in the dashboard LIVE while the agent is still running
- agentlens.log() messages visible in real-time inside each span
- How long-running agents look in the topology graph incrementally

Run this script, then watch http://localhost:3000 — you'll see each node
appear on the graph one by one as the agent progresses through its work.
"""
import time

import agentlens

# ---------------------------------------------------------------------------
# Configuration — streaming=True is the key flag.
# Each span is sent to the server the moment it finishes, not at trace end.
# ---------------------------------------------------------------------------
agentlens.configure(
    server_url="http://localhost:3000",
    streaming=True,   # <-- enable real-time span delivery
)


# ---------------------------------------------------------------------------
# Simulated long-running agent helpers
# ---------------------------------------------------------------------------

def _retrieve_documents(query: str) -> list[str]:
    """Simulate a vector-store retrieval with progressive results."""
    time.sleep(1.5)
    return [
        "Doc[0]: Overview of transformer attention mechanisms",
        "Doc[1]: Benchmark results for LLaMA 3 vs GPT-4",
        "Doc[2]: Cost analysis of fine-tuning vs prompting",
    ]


def _rerank_documents(docs: list[str]) -> list[str]:
    """Cross-encoder reranking — slightly expensive."""
    time.sleep(1.0)
    # Simulate reranker reversing priority
    return list(reversed(docs))


def _generate_answer(docs: list[str], query: str) -> str:
    """Simulate main LLM generation (longest step)."""
    time.sleep(2.0)
    return (
        f"Based on the retrieved context, here is the answer to '{query}':\n\n"
        "Cost analysis shows prompting GPT-4o is 3-5x cheaper than fine-tuning "
        "for most production use-cases. LLaMA 3 achieves 87% of GPT-4 quality "
        "on reasoning tasks while running on consumer hardware."
    )


def _validate_answer(answer: str) -> dict:
    """Simulate a lightweight answer validation / guardrail check."""
    time.sleep(0.7)
    return {
        "is_grounded": True,
        "confidence": 0.91,
        "flagged_claims": [],
    }


def _format_response(answer: str, validation: dict) -> str:
    """Final formatting pass."""
    time.sleep(0.4)
    confidence_pct = int(validation["confidence"] * 100)
    return f"{answer}\n\n[Confidence: {confidence_pct}% | Grounded: {validation['is_grounded']}]"


# ---------------------------------------------------------------------------
# Agent — with streaming=True each span below is transmitted to the server
# the instant its 'with' block exits, so the dashboard updates in real-time.
# ---------------------------------------------------------------------------

@agentlens.trace(name="RAGAgent")
def run_rag_agent(query: str) -> str:
    """Retrieval-Augmented Generation agent — streams span-by-span to dashboard."""

    # Step 1: retrieve (watch this node appear on the graph first)
    with agentlens.span("retrieve_documents", "tool_call") as s:
        agentlens.log("Starting vector store retrieval", query=query)
        print("  [1/5] retrieve_documents... ", end="", flush=True)
        docs = _retrieve_documents(query)
        s.set_output(f"Retrieved {len(docs)} documents")
        agentlens.log("Retrieval complete", doc_count=len(docs))
        print("done  → span sent to dashboard")

    time.sleep(0.3)  # brief pause so you can watch the graph update

    # Step 2: rerank
    with agentlens.span("rerank_documents", "tool_call") as s:
        agentlens.log("Reranking with cross-encoder model")
        print("  [2/5] rerank_documents... ", end="", flush=True)
        reranked = _rerank_documents(docs)
        s.set_output(f"Top doc: {reranked[0][:60]}...")
        agentlens.log("Reranking complete", top_doc=reranked[0])
        print("done  → span sent to dashboard")

    time.sleep(0.3)

    # Step 3: generate (longest step — LLM call with cost tracking)
    with agentlens.span("generate_answer", "llm_call") as s:
        agentlens.log("Calling GPT-4o for answer generation", model="gpt-4o")
        print("  [3/5] generate_answer... ", end="", flush=True)
        answer = _generate_answer(reranked, query)
        s.set_output(answer[:300])
        s.set_cost("gpt-4o", input_tokens=1800, output_tokens=320)
        agentlens.log("Generation complete", output_tokens=320)
        print("done  → span sent to dashboard")

    time.sleep(0.3)

    # Step 4: validate
    with agentlens.span("validate_answer", "tool_call") as s:
        agentlens.log("Running guardrail validation check")
        print("  [4/5] validate_answer... ", end="", flush=True)
        validation = _validate_answer(answer)
        s.set_output(str(validation))
        agentlens.log(
            "Validation passed",
            confidence=validation["confidence"],
            grounded=validation["is_grounded"],
        )
        print("done  → span sent to dashboard")

    time.sleep(0.3)

    # Step 5: format
    with agentlens.span("format_response", "tool_call") as s:
        agentlens.log("Formatting final response")
        print("  [5/5] format_response... ", end="", flush=True)
        final = _format_response(answer, validation)
        s.set_output(final[:200])
        print("done  → span sent to dashboard")

    return final


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query = "What is the cost-quality trade-off between GPT-4 and open-source LLMs?"

    print("\nStreaming demo — open http://localhost:3000 NOW")
    print("Watch the topology graph update in real-time as each span completes.\n")
    print(f"Query: '{query}'")
    print("-" * 60)

    result = run_rag_agent(query)

    print("-" * 60)
    print("\nFinal answer preview:")
    print(result[:300])
    print("\nAll spans sent. Full trace visible at http://localhost:3000")
