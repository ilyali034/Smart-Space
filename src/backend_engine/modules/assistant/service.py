import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

import httpx

from backend_engine.modules.assistant.config import EngineConfig, ChatMessage, OllamaError, OllamaErrorKind, ToolCall
from backend_engine.modules.assistant.dto import AssistantRequestDto, AssistantResponseDto, CommandExecutionDto
from backend_engine.modules.assistant.ollama import OllamaClient
from backend_engine.modules.devices.service import DeviceService
from backend_engine.shared.auth.principal import Permission, Principal, require

log = logging.getLogger(__name__)
_MAX_DEVICES_IN_PROMPT = 60


class ChatBackend(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        on_token: Callable[[str], None] | None = None,
    ) -> ChatMessage: ...


class SmartSpaceClient:
    def __init__(self, device_service: DeviceService, actor: Principal) -> None:
        self._device_service = device_service
        self._actor = actor

    async def list_devices(self, limit: int = _MAX_DEVICES_IN_PROMPT) -> list[dict[str, Any]]:
        return await self._device_service.list_devices(self._actor, limit=limit)

    async def execute_command(
        self,
        slug: str,
        command_id: str,
        action: str,
        parameters: dict[str, Any],
        *,
        source: str = "assistant",
    ) -> dict[str, Any]:
        from backend_engine.modules.commands.dto import SubmitCommandDto, CommandSource
        from backend_engine.modules.commands.service import CommandService

        dto = SubmitCommandDto(
            command_id=UUID(command_id),
            action=action,
            parameters=parameters,
            source=CommandSource(source),
        )
        result = await CommandService.submit(self._actor, slug, dto)
        return {
            "ok": result.status in ("approved", "dispatched", "acknowledged", "awaiting_confirmation"),
            "status": result.status,
            "reasons": result.decision_reasons,
            "command_id": str(result.command_id),
        }

    async def confirm_command(self, command_id: str, confirm: bool) -> dict[str, Any]:
        from backend_engine.modules.commands.service import CommandService

        result = await CommandService.confirm(self._actor, UUID(command_id)) if confirm else await CommandService.reject(self._actor, UUID(command_id))
        return {
            "ok": result.status in ("approved", "dispatched", "acknowledged"),
            "status": result.status,
            "reasons": result.decision_reasons,
            "command_id": str(result.command_id),
        }


class ToolExecutor:
    def __init__(self, api: SmartSpaceClient, *, ack_wait: float, max_commands: int) -> None:
        self._api = api
        self._ack_wait = ack_wait
        self._max_commands = max_commands
        self._commands: list[dict[str, Any]] = []
        self._turn_commands = 0

    def new_turn(self) -> None:
        self._turn_commands = 0

    @property
    def commands(self) -> list[dict[str, Any]]:
        return self._commands

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "execute_command":
            return await self._execute_command(arguments)
        if name == "confirm_command":
            return await self._confirm_command(arguments)
        return {"ok": False, "error": {"code": "unknown_tool", "message": f"Unknown tool: {name}"}}

    async def _execute_command(self, args: dict[str, Any]) -> dict[str, Any]:
        if self._turn_commands >= self._max_commands:
            return {"ok": False, "error": {"code": "too_many_commands", "message": "Command limit reached for this turn"}}
        self._turn_commands += 1

        slug = args.get("slug")
        action = args.get("action")
        parameters = args.get("parameters", {})
        command_id = args.get("command_id") or __import__("uuid").uuid4().hex

        result = await self._api.execute_command(slug, command_id, action, parameters)
        self._commands.append(result)
        return result

    async def _confirm_command(self, args: dict[str, Any]) -> dict[str, Any]:
        command_id = args.get("command_id")
        confirm = args.get("confirm", True)
        result = await self._api.confirm_command(command_id, confirm)
        self._commands.append(result)
        return result


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Send a command to a device. Returns the command status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Device slug (e.g. living_lamp)"},
                    "action": {"type": "string", "description": "Action name (e.g. turn_on, set_brightness)"},
                    "parameters": {"type": "object", "description": "Action parameters", "default": {}},
                    "command_id": {"type": "string", "description": "Optional: client-generated UUID for idempotency"},
                },
                "required": ["slug", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_command",
            "description": "Confirm or reject a command that requires human confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command_id": {"type": "string", "description": "Command UUID"},
                    "confirm": {"type": "boolean", "description": "True to approve, False to reject", "default": True},
                },
                "required": ["command_id"],
            },
        },
    },
]


def _device_view(device: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": device.get("slug"),
        "name": device.get("name"),
        "type": device.get("type"),
        "availability": device.get("availability"),
        "actions": device.get("capabilities", []),
        "state": device.get("state", {}),
    }


def build_system_prompt(language: str, devices_block: str) -> str:
    if language == "ru":
        return (
            "Ты — голосовой ассистент умного дома Smart Space. "
            "Твоя задача — управлять устройствами через инструменты. "
            "Всегда вызывай инструменты для действий; не придумывай результаты. "
            "Если устройство требует подтверждения, спроси пользователя и вызови confirm_command. "
            "Отвечай кратко на русском.\n\n"
            f"Доступные устройства:\n{devices_block or '(нет)'}"
        )
    return (
        "You are the Smart Space voice assistant. "
        "Control devices via tools; never fabricate results. "
        "If a command requires confirmation, ask the user and call confirm_command. "
        "Reply concisely in English.\n\n"
        f"Available devices:\n{devices_block or '(none)'}"
    )


def fallback_text(language: str, commands: list[dict[str, Any]]) -> str:
    if not commands:
        return "Ничего не выполнено." if language == "ru" else "Nothing executed."
    done = sum(1 for c in commands if c.get("ok") or c.get("status") in ("dispatched", "acknowledged", "approved", "awaiting_confirmation"))
    if language == "ru":
        return f"Выполнено команд: {done}."
    return f"Executed {done} command(s)."


class OllamaEngine:
    def __init__(
        self,
        llm: ChatBackend,
        api: SmartSpaceClient,
        *,
        language: str = "ru",
        ack_wait: float = 5.0,
        max_steps: int = 5,
        max_commands_per_turn: int = 3,
        history_turns: int = 6,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._llm = llm
        self._api = api
        self._lang = language
        self._max_steps = max_steps
        self._history_limit = history_turns * 2
        self._history: list[dict[str, str]] = []
        self._tools = executor or ToolExecutor(api, ack_wait=ack_wait, max_commands=max_commands_per_turn)
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        self._history.clear()

    async def respond(self, user_text: str, *, on_token: Callable[[str], None] | None = None) -> AssistantResponseDto:
        async with self._lock:
            return await self._respond(user_text.strip(), on_token)

    async def _respond(self, user_text: str, on_token: Callable[[str], None] | None) -> AssistantResponseDto:
        if not user_text:
            return AssistantResponseDto(text="")

        self._tools.new_turn()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(self._lang, await self._devices_block())},
            *self._history,
            {"role": "user", "content": user_text},
        ]
        final = ""
        steps = 0
        for steps in range(1, self._max_steps + 1):
            msg = await self._llm.chat(messages, TOOLS, on_token=on_token)
            messages.append(msg.as_history())
            if not msg.tool_calls:
                final = msg.content
                break
            for call in msg.tool_calls:
                if call.parse_error:
                    result: dict[str, Any] = {"ok": False, "error": {"code": "invalid_arguments", "message": call.parse_error}}
                else:
                    result = await self._tools.execute(call.name, call.arguments)
                log.info("tool %s(%s) -> %s", call.name, call.arguments, {k: result.get(k) for k in ("ok", "status", "executed")})
                messages.append({"role": "tool", "tool_name": call.name, "content": json.dumps(result, ensure_ascii=False)})
        else:
            log.warning("no final answer after %d steps", self._max_steps)

        commands = list(self._tools.commands)
        text = final or fallback_text(self._lang, commands)
        self._remember(user_text, text)

        cmd_dtos = [
            CommandExecutionDto(
                command_id=c.get("command_id", ""),
                slug=c.get("slug", ""),
                action=c.get("action", ""),
                parameters=c.get("parameters", {}),
                ok=c.get("ok", False),
                status=c.get("status", "unknown"),
                reasons=c.get("reasons", []),
                error=c.get("error"),
            )
            for c in commands
        ]
        return AssistantResponseDto(text=text, commands=cmd_dtos, steps=steps)

    async def _devices_block(self) -> str:
        try:
            devices = await self._api.list_devices(limit=_MAX_DEVICES_IN_PROMPT)
        except Exception as exc:
            log.warning("device list unavailable: %s", exc)
            return "(device list unavailable right now)"
        lines = []
        for d in devices:
            v = _device_view(d)
            lines.append(
                f"- {v['slug']} | {v['name']} | {v['type']} | {v['availability']} | "
                f"{','.join(v['actions']) or 'read-only'} | {v['state']}"
            )
        return "\n".join(lines)

    def _remember(self, user: str, assistant: str) -> None:
        self._history += [{"role": "user", "content": user}, {"role": "assistant", "content": assistant}]
        del self._history[: -self._history_limit]


class AssistantService:
    def __init__(
        self,
        device_service: DeviceService,
        config: EngineConfig,
        llm_client: httpx.AsyncClient,
    ) -> None:
        self._device_service = device_service
        self._config = config
        self._llm_client = llm_client
        self._sessions: dict[UUID, OllamaEngine] = {}

    def _get_or_create_engine(self, actor: Principal, session_id: UUID | None) -> OllamaEngine:
        sid = session_id or UUID(int=0)
        if sid not in self._sessions:
            api = SmartSpaceClient(self._device_service, actor)
            llm = OllamaClient(
                self._llm_client,
                model=self._config.model,
                keep_alive=self._config.keep_alive,
                temperature=self._config.temperature,
                num_ctx=self._config.num_ctx,
            )
            self._sessions[sid] = OllamaEngine(
                llm,
                api,
                language=self._config.language,
                ack_wait=self._config.ack_wait,
                max_steps=self._config.max_steps,
                max_commands_per_turn=self._config.max_commands_per_turn,
                history_turns=self._config.history_turns,
            )
        return self._sessions[sid]

    async def respond(self, actor: Principal, dto: AssistantRequestDto) -> AssistantResponseDto:
        require(actor, Permission.COMMAND_CREATE)
        engine = self._get_or_create_engine(actor, dto.session_id)
        return await engine.respond(dto.text)

    def reset_session(self, session_id: UUID) -> None:
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        self._sessions.clear()