from typing import Protocol
from uuid import UUID

from backend_engine.modules.commands.entity import CommandEntity


class CommandDispatcher(Protocol):
    async def dispatch(self, command: CommandEntity) -> None: ...


class FakeDispatcher:
    def __init__(self) -> None:
        self.dispatched: list[UUID] = []

    async def dispatch(self, command: CommandEntity) -> None:
        self.dispatched.append(command.command_id)
