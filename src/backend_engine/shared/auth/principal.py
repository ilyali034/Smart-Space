from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    GATEWAY = "gateway"  # service token for MQTT gateway


class Permission(StrEnum):
    DEVICE_READ = "device:read"
    DEVICE_WRITE = "device:write"
    DEVICE_DELETE = "device:delete"
    DEVICE_REPORT = "device:report"  # state/availability from gateway


_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.USER: frozenset({Permission.DEVICE_READ, Permission.DEVICE_WRITE}),
    Role.VIEWER: frozenset({Permission.DEVICE_READ}),
    Role.GATEWAY: frozenset({Permission.DEVICE_READ, Permission.DEVICE_REPORT}),
}


class AuthError(Exception): ...
class Unauthenticated(AuthError): ...
class Forbidden(AuthError):
    def __init__(self, permission: Permission) -> None:
        super().__init__(f"missing permission: {permission}")


@dataclass(frozen=True, slots=True)
class Principal:
    id: str
    role: Role

    def can(self, permission: Permission) -> bool:
        return permission in _ROLE_PERMISSIONS[self.role]


def require(principal: Principal, permission: Permission) -> None:
    if not principal.can(permission):
        raise Forbidden(permission)