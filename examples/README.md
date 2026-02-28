# AgentLens SDK Examples

Practical demos showing AgentLens SDK features: tracing, spans, cost tracking, streaming, and multi-agent workflows.

## Prerequisites

1. **Start the AgentLens server:**
   ```bash
   docker run -p 3000:3000 tranhoangtu/agentlens:0.2.0
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Examples

### 1. Basic Usage (`basic_usage.py`)
Single-agent trace with tool calls and LLM spans. Best starting point.
```bash
python basic_usage.py
```

### 2. Multi-Agent (`multi_agent.py`)
Three-agent pipeline: Planner → Researcher → Writer with handoffs and cost tracking across different models.
```bash
python multi_agent.py
```

### 3. Streaming (`streaming.py`)
Long-running agent with `streaming=True` — watch spans appear in the dashboard in real-time.
```bash
python streaming.py
```

## View Results

Open **http://localhost:3000** after running any example. Each script prints the trace URL directly.
