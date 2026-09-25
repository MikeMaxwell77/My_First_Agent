"""Provider-independent messages and observable run results."""
from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    name: str
    arguments: str
    call_id: str = "call"


@dataclass
class ModelResponse:
    calls: list[ToolCall] = field(default_factory=list)
    final_answer: str = ""
    determination: str = "UNKNOWN"
    reason: str = ""


class ModelClient(Protocol):
    def generate(self, state: list[dict], tools: list[dict]) -> ModelResponse: ...


@dataclass
class ApprovalRequest:
    approval_id: str
    tool: str
    arguments: dict
    reason: str
    status: str
    created_at: str


@dataclass
class AgentResult:
    trace_id: str
    final_answer: str = ""
    determination: str = "UNKNOWN"
    reason: str = ""
    tools_requested: list = field(default_factory=list)
    tools_executed: list = field(default_factory=list)
    tools_blocked: list = field(default_factory=list)
    tool_arguments: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    approval_requests: list = field(default_factory=list)
    iteration_count: int = 0
    latency_seconds: float = 0
    errors: list = field(default_factory=list)
    events: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def __getitem__(self, key):
        return getattr(self, key)
