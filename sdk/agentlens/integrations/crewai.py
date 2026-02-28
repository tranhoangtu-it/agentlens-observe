"""CrewAI integration: patch Crew.kickoff and Task.execute to emit spans."""
import logging
import uuid

from agentlens.tracer import SpanData, _current_trace, _now_ms

logger = logging.getLogger("agentlens.integrations.crewai")
_patched = False


def patch_crewai():
    """Call once at startup to auto-instrument all CrewAI runs."""
    global _patched
    if _patched:
        return
    try:
        import crewai
        _patch_crew(crewai.Crew)
        _patch_task(crewai.Task)
        _patched = True
        logger.info("AgentLens: CrewAI patched successfully")
    except ImportError:
        raise ImportError("crewai required: pip install agentlens[crewai]")


def _patch_crew(Crew):
    original_kickoff = Crew.kickoff

    def patched_kickoff(self, *args, **kwargs):
        active = _current_trace.get()
        start = _now_ms()
        result = original_kickoff(self, *args, **kwargs)
        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"crew:{getattr(self, 'name', 'Crew')}",
                type="agent_run",
                start_ms=start,
                end_ms=_now_ms(),
                output=str(result)[:2048],
            )
            active.spans.append(span)
        return result

    Crew.kickoff = patched_kickoff


def _patch_task(Task):
    original_execute = getattr(Task, "execute_sync", None) or getattr(Task, "_execute", None)
    if not original_execute:
        return

    method_name = "execute_sync" if hasattr(Task, "execute_sync") else "_execute"

    def patched_execute(self, *args, **kwargs):
        active = _current_trace.get()
        start = _now_ms()
        result = original_execute(self, *args, **kwargs)
        if active:
            span = SpanData(
                span_id=str(uuid.uuid4()),
                parent_id=active.current_span_id(),
                name=f"task:{getattr(self, 'description', 'task')[:60]}",
                type="tool_call",
                start_ms=start,
                end_ms=_now_ms(),
                output=str(result)[:2048],
            )
            active.spans.append(span)
        return result

    setattr(Task, method_name, patched_execute)
