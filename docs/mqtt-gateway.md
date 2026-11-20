# MQTT command delivery

The backend publishes each approved command to MQTT. Configure the broker with
`MQTT_HOST` (default `localhost`) and optionally `MQTT_PORT` (default `1883`),
`MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_TLS` (default `false`),
`MQTT_KEEPALIVE` (default `30` seconds), and `MQTT_TOPIC_PREFIX` (default
`smart-space/devices`).

For a device with ID `d2cf...`, the gateway subscribes to
`smart-space/devices/d2cf.../commands` (or the configured prefix followed by
`/{device_id}/commands`). The backend publishes a UTF-8 JSON object with QoS 1
and `retain=false`:

```json
{
  "command_id": "<idempotency UUID>",
  "device_id": "<device UUID>",
  "action": "turn_on",
  "parameters": {},
  "correlation_id": null
}
```

QoS 1 is at-least-once delivery, so gateways must deduplicate by `command_id`.
Successful broker publication only moves the backend command to `dispatched`;
it does not mean the device executed it. The gateway must report execution via
the backend acknowledgement API, which transitions the command to
`acknowledged` or `failed`.

Use broker ACLs so the backend can publish only to `.../commands` and each
gateway can subscribe only to its assigned device topic. Enable `MQTT_TLS=true`
and use credentials outside local development. The backend currently opens a
broker connection for each approved command; it does not run an MQTT subscriber
or implement the device gateway.