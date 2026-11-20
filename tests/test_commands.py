import uuid

import pytest

from backend_engine.modules.commands.entity import (
    CommandEntity,
    CommandStatus,
    InvalidStatusTransition,
    transition_status,
)


def test_invalid_status_transition_is_rejected() -> None:
    entity = CommandEntity(
        command_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        action="turn_on",
        parameters={},
        status=CommandStatus.PENDING,
        source="api",
        requested_by="test",
    )
    with pytest.raises(InvalidStatusTransition):
        transition_status(entity, CommandStatus.DISPATCHED)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (CommandStatus.PENDING, CommandStatus.APPROVED),
        (CommandStatus.AWAITING_CONFIRMATION, CommandStatus.APPROVED),
        (CommandStatus.APPROVED, CommandStatus.DISPATCHED),
        (CommandStatus.DISPATCHED, CommandStatus.ACKNOWLEDGED),
    ],
)
def test_valid_status_transitions(old: CommandStatus, new: CommandStatus) -> None:
    entity = CommandEntity(
        command_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        action="turn_on",
        parameters={},
        status=old,
        source="api",
        requested_by="test",
    )
    transition_status(entity, new)
    assert entity.status == new


@pytest.mark.parametrize("terminal", [
    CommandStatus.REJECTED,
    CommandStatus.EXPIRED,
    CommandStatus.CANCELLED,
    CommandStatus.ACKNOWLEDGED,
    CommandStatus.FAILED,
    CommandStatus.TIMED_OUT,
])
def test_terminal_statuses_cannot_change(terminal: CommandStatus) -> None:
    entity = CommandEntity(
        command_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        action="turn_on",
        parameters={},
        status=terminal,
        source="api",
        requested_by="test",
    )
    with pytest.raises(InvalidStatusTransition):
        transition_status(entity, CommandStatus.APPROVED)
