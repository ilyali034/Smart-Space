import httpx
import pytest

from smart_space_desktop.core.api_client import ApiClient
from smart_space_desktop.core.errors import AppError, ErrorKind


def client(handler):
    return ApiClient("http://test", "ss_secret", transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "code,kind",
    [
        (400, ErrorKind.BAD_REQUEST),
        (401, ErrorKind.UNAUTHORIZED),
        (403, ErrorKind.FORBIDDEN),
        (404, ErrorKind.NOT_FOUND),
        (409, ErrorKind.CONFLICT),
        (422, ErrorKind.VALIDATION),
        (500, ErrorKind.SERVER),
        (503, ErrorKind.SERVER),
    ],
)
def test_status_mapping(code, kind):
    c = client(lambda r: httpx.Response(code, json={"detail": "x"}))
    with pytest.raises(AppError) as ei:
        c.get("/api/v1/devices")
    assert ei.value.kind is kind
    assert ei.value.status_code == code


def test_backend_detail_only_in_technical():
    c = client(lambda r: httpx.Response(409, json={"detail": "device disabled"}))
    with pytest.raises(AppError) as ei:
        c.get("/x")
    assert "device disabled" in ei.value.technical
    assert "device disabled" not in ei.value.message


def test_422_list_detail_does_not_crash():
    c = client(lambda r: httpx.Response(422, json={"detail": [{"msg": "bad"}]}))
    with pytest.raises(AppError) as ei:
        c.get("/x")
    assert ei.value.kind is ErrorKind.VALIDATION


def test_timeout_and_connect_error():
    def timeout(r):
        raise httpx.ReadTimeout("t", request=r)

    def refused(r):
        raise httpx.ConnectError("c", request=r)

    with pytest.raises(AppError) as e1:
        client(timeout).get("/x")
    assert e1.value.kind is ErrorKind.TIMEOUT
    with pytest.raises(AppError) as e2:
        client(refused).get("/x")
    assert e2.value.kind is ErrorKind.NETWORK


def test_invalid_json_and_204():
    with pytest.raises(AppError) as ei:
        client(lambda r: httpx.Response(200, content=b"not json")).get("/x")
    assert ei.value.kind is ErrorKind.BAD_RESPONSE
    assert client(lambda r: httpx.Response(204)).delete("/x") is None


def test_bad_base_url():
    c = ApiClient("localhost:8000", None)  # no scheme
    with pytest.raises(AppError) as ei:
        c.get("/x")
    assert ei.value.kind is ErrorKind.BAD_URL


def test_bearer_header_sent_and_not_in_error_text():
    seen = {}

    def h(r):
        seen["auth"] = r.headers.get("authorization")
        return httpx.Response(401)

    with pytest.raises(AppError) as ei:
        client(h).get("/x")
    assert seen["auth"] == "Bearer ss_secret"
    assert "ss_secret" not in (ei.value.technical or "") + ei.value.message
