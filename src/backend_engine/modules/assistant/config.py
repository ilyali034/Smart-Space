import enum

import os

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

@dataclass(frozen=True, slots=True)
class EngineConfig:
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"  # any Ollama model with tool support (llama3.1, qwen2.5, mistral-nemo, ...)
    ollama_timeout: float = 120.0  # the first request loads the model into memory: be generous
    keep_alive: str = "30m"  # keep the model loaded between voice commands
    temperature: float = 0.1  # low: tool calling must be predictable
    num_ctx: int = 4096
    api_url: str = "http://localhost:8000"
    api_token: str = ""
    language: str = "ru"  # "ru" or "en": language of the system prompt and fallback replies
    ack_wait: float = 5.0  # seconds to wait for the device to acknowledge a command
    max_steps: int = 5  # model <-> tools round trips per user message
    max_commands_per_turn: int = 3  # hard cap, protects against a looping model
    history_turns: int = 6

    @classmethod
    def from_env(cls) -> "EngineConfig":
        env = os.getenv
        token = env("SMARTSPACE_API_TOKEN", "")
        if not token:
            raise RuntimeError("SMARTSPACE_API_TOKEN is not set")
        d = cls()
        return cls(
            ollama_url=env("OLLAMA_URL", d.ollama_url).rstrip("/"),
            model=env("OLLAMA_MODEL", d.model),
            ollama_timeout=float(env("OLLAMA_TIMEOUT", d.ollama_timeout)),
            keep_alive=env("OLLAMA_KEEP_ALIVE", d.keep_alive),
            temperature=float(env("OLLAMA_TEMPERATURE", d.temperature)),
            num_ctx=int(env("OLLAMA_NUM_CTX", d.num_ctx)),
            api_url=env("SMARTSPACE_API_URL", d.api_url).rstrip("/"),
            api_token=token,
            language=env("ASSISTANT_LANG", d.language),
            ack_wait=float(env("ASSISTANT_ACK_WAIT", d.ack_wait)),
            max_steps=int(env("ASSISTANT_MAX_STEPS", d.max_steps)),
        )
