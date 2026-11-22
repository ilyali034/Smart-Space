"""MQTT -> backend gateway: turns device MQTT traffic into backend HTTP calls.

    status    -> PUT  /api/v1/devices/{slug}/availability
    telemetry -> PUT  /api/v1/devices/{slug}/state
    ack       -> POST /api/v1/commands/{command_id}/ack
"""
