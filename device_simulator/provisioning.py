"""Make sure every virtual device exists in the backend and learn its real id."""

import logging
from uuid import UUID

import httpx

from device_simulator.devices import DeviceSpec

log = logging.getLogger(__name__)
API = "/api/v1"
_PAGE = 500


async def ensure_registered(client: httpx.AsyncClient, specs: list[DeviceSpec]) -> dict[str, UUID]:
    existing: dict[str, dict] = {}
    offset = 0
    while True:
        r = await _check(await client.get(f"{API}/devices", params={"limit": _PAGE, "offset": offset}))
        page = r.json()
        existing.update({d["slug"]: d for d in page})
        if len(page) < _PAGE:
            break
        offset += _PAGE

    ids: dict[str, UUID] = {}
    for spec in specs:
        found = existing.get(spec.slug)
        if found is not None:
            if found["type"] != spec.device_type:
                log.warning("%s exists in backend as type %s, simulator expects %s", spec.slug, found["type"], spec.device_type)
            ids[spec.slug] = UUID(found["id"])
            continue
        r = await _check(
            await client.post(
                f"{API}/devices",
                json={
                    "slug": spec.slug,
                    "name": spec.slug.replace("_", " ").title(),
                    "type": spec.device_type,
                    "capabilities": list(spec.capabilities),
                },
            )
        )
        ids[spec.slug] = UUID(r.json()["id"])
        log.info("registered %s in backend", spec.slug)
    return ids


async def _check(resp: httpx.Response) -> httpx.Response:
    if resp.status_code in (401, 403):
        raise RuntimeError(f"backend refused SIM_API_TOKEN ({resp.status_code}); it needs role user or admin")
    resp.raise_for_status()
    return resp
