class CommandError(Exception): pass


class CommandNotFound(CommandError):
    def __init__(self, command_id: object) -> None:
        super().__init__(f"command not found: {command_id}")


class CommandConflict(CommandError):
    def __init__(self, command_id: object) -> None:
        super().__init__(f"command_id already used with a different request: {command_id}")


class HumanConfirmationRequired(CommandError):
    def __init__(self) -> None:
        super().__init__("confirmation requires a human principal")
