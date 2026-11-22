"""Run:  python -m device_simulator

Without SIM_API_URL/SIM_API_TOKEN the devices get stable fallback ids that do NOT exist in
the backend; set them (token with role user/admin) so the simulator registers its devices."""

import asyncio
import logging
from uuid import UUID

import httpx

from device_simulator.config import SimConfig, fallback_id
from device_simulator.devices import FLEETS, DeviceSpec, build_fleet
from device_simulator.provisioning import ensure_registered
from device_simulator.runner import DeviceRunner

log = logging.getLogger("device_simulator")


async def resolve_ids(cfg: SimConfig, specs: list[DeviceSpec]) -> dict[str, UUID]:
    ids: dict[str, UUID] = {}
    if cfg.can_provision:
        async with httpx.AsyncClient(
            base_url=cfg.api_url or "", headers={"Authorization": f"Bearer {cfg.api_token}"}, timeout=10.0
        ) as http:
            ids.update(await ensure_registered(http, specs))
    ids.update(cfg.fixed_ids)
    for spec in specs:
        if spec.slug not in ids:
            ids[spec.slug] = fallback_id(spec.slug)
            log.warning("%s: no backend id (set SIM_API_URL + SIM_API_TOKEN); using fallback %s", spec.slug, ids[spec.slug])
    return ids


async def main() -> None:
    cfg = SimConfig.from_env()
    specs = [s for name in cfg.fleets for s in FLEETS[name]]
    devices = build_fleet(list(cfg.fleets))
    ids = await resolve_ids(cfg, specs)
    for d in devices:
        d.device_id = ids[d.slug]
        log.info("%-18s %-20s %s", d.slug, d.device_type, d.device_id)
    log.info("MQTT %s:%s prefix=%s interval=%ss", cfg.mqtt_host, cfg.mqtt_port, cfg.topic_prefix, cfg.interval)
    await asyncio.gather(*(DeviceRunner(d, cfg).run() for d in devices))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("stopped")
