from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssistantRequestDto(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None


class CommandExecutionDto(BaseModel):
    command_id: str
    slug: str
    action: str
    parameters: dict = Field(default_factory=dict)
    ok: bool
    status: str
    reasons: list[str] = Field(default_factory=list)
    error: str | None = None


class AssistantResponseDto(BaseModel):
    text: str
    commands: list[CommandExecutionDto] = Field(default_factory=list)
    steps: int = 0
    session_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)