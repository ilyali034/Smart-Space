import asyncio
import contextlib
import json
import logging
import socket
from collections import OrderedDict
from collections.abc import Coroutine
from typing import Any

import aiomqtt

from device_simulator.config import SimConfig
from device_simulator.devices import SimDevice
from device_simulator.faults import Faults
from device_simulator.mqtt.publisher import DevicePublisher, status_payload
from device_simulator.mqtt.topics import Topics

_RESULT_MEMORY = 500


class DeviceRunner:
    """One virtual device = one MQTT client with its own Last Will, like real hardware."""

    def __init__(self, device: SimDevice, cfg: SimConfig) -> None:
        assert device.device_id is not None, "device id must be assigned before running"
        self.device = device
        self._cfg = cfg
        self._topics = Topics(cfg.topic_prefix)
        self._log = logging.getLogger(f"device_simulator.{device.slug}")
        self._pub: DevicePublisher | None = None
        self._client: aiomqtt.Client | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        # QoS 1 may deliver a command twice: remember results and never execute twice
        self._results: OrderedDict[str, bool] = OrderedDict()

    async def run(self) -> None:
        delay = 1.0
        while True:
            try:
                await self._session()
                delay = 3.0  # session ended on purpose (simulated crash): "reboot" delay
            except aiomqtt.MqttError as exc:
                self._log.warning("MQTT connection lost (%s); retrying in %.0fs", exc, delay)
                delay = min(delay * 2, 15.0)
            await asyncio.sleep(delay)

    async def _session(self) -> None:
        dev, topics = self.device, self._topics
        assert dev.device_id is not None
        will = aiomqtt.Will(topic=topics.status(dev.device_id), payload=status_payload(dev.device_id, False), qos=1, retain=True)
        async with aiomqtt.Client(
            hostname=self._cfg.mqtt_host,
            port=self._cfg.mqtt_port,
            username=self._cfg.mqtt_username,
            password=self._cfg.mqtt_password,
            keepalive=self._cfg.mqtt_keepalive,
            identifier=f"sim-{dev.slug}",
            will=will,
        ) as client:
            self._client = client
            pub = self._pub = DevicePublisher(client, topics, dev.device_id)
            await client.subscribe(topics.commands(dev.device_id), qos=1)
            await client.subscribe(topics.control, qos=1)
            await pub.status(dev.online)
            if dev.online:
                await pub.telemetry(dev.state())
            self._log.info("online (%s)", dev.device_type)
            ticker = asyncio.create_task(self._telemetry_loop(pub))
            try:
                async for message in client.messages:
                    await self._dispatch(str(message.topic), bytes(message.payload))  # type: ignore[arg-type]
            except asyncio.CancelledError:
                with contextlib.suppress(Exception):  # clean shutdown: say goodbye (a Will is only for crashes)
                    await asyncio.wait_for(pub.status(False), 2.0)
                raise
            finally:
                ticker.cancel()
                for t in list(self._tasks):
                    t.cancel()
                self._client = self._pub = None

    async def _telemetry_loop(self, pub: DevicePublisher) -> None:
        while True:
            await asyncio.sleep(self._cfg.interval)
            if self.device.online:
                self.device.tick(self._cfg.interval)
                await pub.telemetry(self.device.state())

    async def _dispatch(self, topic: str, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not an object")
        except (UnicodeDecodeError, ValueError):
            self._log.warning("ignoring malformed message on %s", topic)
            return
        try:
            if topic == self._topics.control:
                await self._on_control(data)
            else:
                await self._on_command(data)
        except Exception:
            self._log.exception("error while handling message on %s", topic)

    # ---- commands ----

    async def _on_command(self, data: dict[str, Any]) -> None:
        dev, pub = self.device, self._pub
        assert pub is not None
        if not dev.online:
            self._log.info("offline: command ignored")  # a real offline device never sees it
            return
        claimed = data.get("device_id")
        if claimed is not None and str(claimed).lower() != str(dev.device_id):
            return
        cid, action, params = data.get("command_id"), data.get("action"), data.get("parameters") or {}
        if not isinstance(cid, str) or not isinstance(action, str) or not isinstance(params, dict):
            self._log.warning("malformed command ignored: %s", data)
            return

        if cid in self._results:
            self._log.info("duplicate command %s: re-acking, not executing again", cid)
            await pub.ack(cid, self._results[cid])
            return

        outcome = dev.faults.next_outcome()
        ok = False if outcome == "fail" else dev.apply_command(action, params)
        self._results[cid] = ok
        while len(self._results) > _RESULT_MEMORY:
            self._results.popitem(last=False)
        self._log.info("command %s %s %s -> ok=%s outcome=%s", cid[:8], action, params, ok, outcome)

        await pub.telemetry(dev.state())  # the device's state changes immediately
        if outcome == "drop":
            self._log.warning("fault: ack for %s is lost", cid[:8])
            return
        self._spawn(self._ack_later(pub, cid, ok, dev.faults.ack_delay, dev.faults.duplicate_ack))

    async def _ack_later(self, pub: DevicePublisher, cid: str, ok: bool, delay: float, twice: bool) -> None:
        if delay:
            await asyncio.sleep(delay)
        await pub.ack(cid, ok)
        if twice:
            await pub.ack(cid, ok)

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)

        def done(t: asyncio.Task[None]) -> None:
            self._tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                self._log.error("background task failed: %r", t.exception())

        task.add_done_callback(done)

    # ---- control topic ----

    async def _on_control(self, data: dict[str, Any]) -> None:
        dev, pub = self.device, self._pub
        assert pub is not None
        if data.get("device") not in (dev.slug, "*"):
            return
        op = data.get("op")
        if op == "offline":
            dev.online = False
            await pub.status(False)
        elif op == "online":
            dev.online = True
            await pub.status(True)
            await pub.telemetry(dev.state())
        elif op == "crash":
            self._log.warning("simulated crash: dropping the connection without goodbye (broker will publish the Will)")
            self._crash()
        elif op == "faults":
            rejected = dev.faults.update(data.get("faults") or {})
            if rejected:
                self._log.warning("invalid fault settings ignored: %s", rejected)
            self._log.info("faults now: %s", dev.faults)
        elif op == "reset":
            dev.faults = Faults()
        elif op == "set":
            if dev.set_state(data.get("state") or {}) and dev.online:
                await pub.telemetry(dev.state())
        else:
            self._log.warning("unknown control op: %r", op)

    def _crash(self) -> None:
        # shutdown() (not close()): the TCP link dies without an MQTT DISCONNECT, so the broker publishes
        # our Last Will, while the file descriptor stays valid and aiomqtt notices the loss and raises
        # MqttError -> run() reconnects ("reboot"). close() would corrupt aiomqtt's event-loop state.
        with contextlib.suppress(Exception):
            assert self._client is not None
            self._client._client.socket().shutdown(socket.SHUT_RDWR)  # type: ignore[attr-defined]
