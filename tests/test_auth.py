import pytest

from backend_engine.shared.auth.principal import Forbidden, Permission, Principal, Role, require
from backend_engine.shared.auth.tokens import generate_token, hash_token


def test_viewer_cannot_write() -> None:
    p = Principal(id="v", role=Role.VIEWER)
    assert p.can(Permission.DEVICE_READ)
    with pytest.raises(Forbidden):
        require(p, Permission.DEVICE_WRITE)


def test_only_admin_deletes() -> None:
    for role in (Role.USER, Role.VIEWER, Role.GATEWAY):
        assert not Principal(id="x", role=role).can(Permission.DEVICE_DELETE)
    assert Principal(id="a", role=Role.ADMIN).can(Permission.DEVICE_DELETE)


def test_token_roundtrip() -> None:
    raw, h = generate_token()
    assert raw.startswith("ss_")
    assert hash_token(raw) == h
    assert raw not in h
