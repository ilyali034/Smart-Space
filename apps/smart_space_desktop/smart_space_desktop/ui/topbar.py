from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget

from smart_space_desktop.core.connection import ConnectionInfo, LinkState
from smart_space_desktop.core.context import AppContext
from smart_space_desktop.core.settings import Settings
from smart_space_desktop.ui.theme import C
from smart_space_desktop.ui.widgets import StatusChip

_CHIP = {
    LinkState.CHECKING: ("Checking…", "muted"),
    LinkState.ONLINE: ("Backend online", "ok"),
    LinkState.NO_TOKEN: ("No token", "warn"),
    LinkState.UNAUTHORIZED: ("Token rejected", "danger"),
    LinkState.UNREACHABLE: ("Offline", "danger"),
    LinkState.DEMO: ("Demo", "warn"),
}


class Topbar(QFrame):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Topbar")
        self.setFixedHeight(64)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(10)

        self.title = QLabel("Dashboard")
        self.title.setObjectName("Title")
        lay.addWidget(self.title, 1)

        self.demo_badge = QLabel("DEMO MODE")
        self.demo_badge.setObjectName("DemoBadge")
        lay.addWidget(self.demo_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.chip = StatusChip()
        lay.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignVCenter)

        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("TopBtn")
        self.refresh_btn.setText("Refresh")
        self.refresh_btn.setToolTip("Refresh (Ctrl+R)")
        self.refresh_btn.clicked.connect(ctx.refresh)
        lay.addWidget(self.refresh_btn)

        notif = QToolButton()
        notif.setObjectName("TopBtn")
        notif.setText("Notifications")
        notif.setToolTip("No notifications")
        notif.setEnabled(False)
        lay.addWidget(notif)

        avatar = QLabel("?")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setToolTip("Role unknown: the backend does not provide /me")
        lay.addWidget(avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        self._on_settings(ctx.settings)
        self._on_conn(ctx.monitor.info)
        ctx.store.changed.connect(self._on_settings)
        ctx.monitor.changed.connect(self._on_conn)

    def set_title(self, text: str) -> None:
        self.title.setText(text)

    def _on_settings(self, s: Settings) -> None:
        self.demo_badge.setVisible(s.demo_mode)

    def _on_conn(self, info: ConnectionInfo) -> None:
        text, tone = _CHIP[info.state]
        self.chip.set_status(text, tone)
        self.chip.setToolTip(info.message or text)
