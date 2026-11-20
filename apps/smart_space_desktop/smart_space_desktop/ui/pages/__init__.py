from smart_space_desktop.ui.pages.placeholder import Availability as A
from smart_space_desktop.ui.pages.placeholder import PlaceholderPage


def build_placeholder_pages() -> dict[str, PlaceholderPage]:
    """Phase 1 stubs. Real pages replace these in Phase 2+."""
    return {
        "dashboard": PlaceholderPage(
            "Dashboard",
            "System summary: total, online, and offline devices. Real data will appear in Phase 2.",
            "GET /api/v1/devices (counts are calculated on the client)",
            A.PLANNED,
        ),
        "rooms": PlaceholderPage(
            "Rooms",
            "The backend has no room entity, only room_id on each device. "
            "Phase 3: group devices by room_id without room names.",
            "GET /api/v1/devices?room_id=",
            A.BACKEND_MISSING,
        ),
        "devices": PlaceholderPage(
            "Devices",
            "Device list, cards, status, and command submission. Phase 3.",
            "GET /api/v1/devices, POST /api/v1/devices/{slug}/command",
            A.PLANNED,
        ),
        "commands": PlaceholderPage(
            "Commands",
            "Command lifecycle (pending → … → acknowledged). The backend has no command list: "
            "Phase 4 will show only commands known to this client.",
            "GET /api/v1/commands/{command_id}",
            A.PLANNED,
        ),
        "automations": PlaceholderPage(
            "Automations",
            "The automation module is missing from the backend. This feature is unavailable.",
            "None",
            A.BACKEND_MISSING,
        ),
        "activity": PlaceholderPage(
            "Activity",
            "The audit_log table exists, but the API for reading it is missing. The event log is unavailable.",
            "None (GET /api/v1/audit is required)",
            A.BACKEND_MISSING,
        ),
        "safety": PlaceholderPage(
            "Safety Center",
            "Confirm or reject commands and trigger the emergency stop. The backend has no list of "
            "commands awaiting confirmation. Phase 4.",
            "POST /api/v1/commands/{id}/confirm|reject, POST /api/v1/system/emergency-stop",
            A.PLANNED,
        ),
        "assistant": PlaceholderPage(
            "AI Assistant",
            "The assistant interface will be added later: the backend has no AI API. "
            "The model workflow is not simulated.",
            "None",
            A.COMING_SOON,
        ),
    }
