"""AgentLens SDK — trace AI agents visually."""
__version__ = "0.1.0"

from .tracer import Tracer

_tracer = Tracer()

# Public API
trace = _tracer.trace
span = _tracer.span
configure = _tracer.configure
current_trace = _tracer.current_trace
