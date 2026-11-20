from typing import NamedTuple


class NavItem(NamedTuple):
    key: str
    label: str
    shortcut: str | None = None


NAV_ITEMS = [
    NavItem("dashboard", "Dashboard", "Ctrl+1"),
    NavItem("rooms", "Rooms", "Ctrl+2"),
    NavItem("devices", "Devices", "Ctrl+3"),
    NavItem("commands", "Commands", "Ctrl+4"),
    NavItem("automations", "Automations"),
    NavItem("activity", "Activity"),
    NavItem("safety", "Safety Center"),
    NavItem("assistant", "AI Assistant"),
]
SETTINGS_ITEM = NavItem("settings", "Settings", "Ctrl+,")


def title_for(key: str) -> str:
    for i in [*NAV_ITEMS, SETTINGS_ITEM]:
        if i.key == key:
            return i.label
    return "Smart Space"
