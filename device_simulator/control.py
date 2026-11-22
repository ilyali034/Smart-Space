"""Send control messages to running virtual devices.

  python -m device_simulator.control offline  living_lamp
  python -m device_simulator.control online   living_lamp
  python -m device_simulator.control crash    living_lamp          # connection dies -> broker publishes the Will
  python -m device_simulator.control faults   living_lamp ack_delay=2 fail_next=1 drop_next=1 duplicate_ack=true
  python -m device_simulator.control reset    living_lamp          # clear faults
  python -m device_simulator.control set      living_temp temperature=31.5
Use '*' as the device to address all of them."""

import argparse
import asyncio
import json
from typing import Any

import aiomqtt

from device_simulator.config import SimConfig
from device_simulator.mqtt.topics import Topics

OPS = ("offline", "online", "crash", "faults", "reset", "set")


def parse_pairs(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs:
        key, sep, raw = pair.partition("=")
        if not sep:
            raise SystemExit(f"expected key=value, got '{pair}'")
        try:
            out[key] = json.loads(raw)  # numbers, true/false
        except ValueError:
            out[key] = raw
    return out


def build_message(op: str, device: str, pairs: list[str]) -> dict[str, Any]:
    msg: dict[str, Any] = {"device": device, "op": op}
    if op == "faults":
        msg["faults"] = parse_pairs(pairs)
    elif op == "set":
        msg["state"] = parse_pairs(pairs)
    return msg


async def send(cfg: SimConfig, message: dict[str, Any]) -> None:
    async with aiomqtt.Client(
        hostname=cfg.mqtt_host, port=cfg.mqtt_port, username=cfg.mqtt_username, password=cfg.mqtt_password
    ) as client:
        await client.publish(Topics(cfg.topic_prefix).control, json.dumps(message), qos=1)


def main() -> None:
    p = argparse.ArgumentParser(prog="device_simulator.control")
    p.add_argument("op", choices=OPS)
    p.add_argument("device", help="slug, or * for all")
    p.add_argument("pairs", nargs="*", help="key=value (for faults / set)")
    args = p.parse_args()
    asyncio.run(send(SimConfig.from_env(), build_message(args.op, args.device, args.pairs)))


if __name__ == "__main__":
    main()
