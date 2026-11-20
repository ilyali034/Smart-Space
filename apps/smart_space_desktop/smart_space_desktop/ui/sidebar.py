from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from smart_space_desktop import __version__
from smart_space_desktop.core.context import AppContext
from smart_space_desktop.core.settings import Settings
from smart_space_desktop.ui.nav import NAV_ITEMS, SETTINGS_ITEM, NavItem
from smart_space_desktop.ui.widgets import repolish


class Sidebar(QFrame):
    navigate = Signal(str)

    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(232)
        self.buttons: dict[str, QPushButton] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 24, 10, 14)
        lay.setSpacing(3)

        logo = QLabel("SMART SPACE")
        logo.setObjectName("Logo")
        logo.setContentsMargins(10, 0, 0, 18)
        lay.addWidget(logo)

        for item in NAV_ITEMS:
            lay.addWidget(self._make(item))
        lay.addStretch(1)
        lay.addWidget(self._make(SETTINGS_ITEM))

        self.info = QLabel()
        self.info.setObjectName("SideInfo")
        self.info.setContentsMargins(10, 10, 0, 0)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lay.addWidget(self.info)
        ver = QLabel(f"v{__version__}")
        ver.setObjectName("SideInfo")
        ver.setContentsMargins(10, 0, 0, 0)
        lay.addWidget(ver)

        self._update_info(ctx.settings)
        ctx.store.changed.connect(self._update_info)

    def _make(self, item: NavItem) -> QPushButton:
        b = QPushButton(item.label)
        b.setObjectName("Nav")
        b.setCheckable(True)
        b.setAutoExclusive(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(f"{item.label} ({item.shortcut})" if item.shortcut else item.label)
        b.clicked.connect(lambda _=False, k=item.key: self.navigate.emit(k))
        self.buttons[item.key] = b
        return b

    def set_current(self, key: str) -> None:
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def _update_info(self, s: Settings) -> None:
        self.info.setText("DEMO MODE" if s.demo_mode else s.base_url)
        self.info.setProperty("demo", s.demo_mode)
        repolish(self.info)
