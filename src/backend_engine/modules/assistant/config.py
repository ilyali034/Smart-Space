import enum

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

class OllamaErrorKind(enum.Enum):
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    NO_TOOLS_SUPPORT = "no_tools_support"
    BAD_RESPONSE = "bad_response"
    HTTP = "http"


class OllamaError(Exception):
    def __init__(self, kind: OllamaErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message 

@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    parse_error: str | None = None  # set when the model produced arguments we could not parse

@dataclass
class ChatMessage:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    def as_history(self) -> dict[str, Any]:
        """The assistant message to append to the conversation (Ollama expects tool_calls echoed back)."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in self.tool_calls]
        return msg
