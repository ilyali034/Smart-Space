from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from smart_space_desktop.core.context import AppContext
from smart_space_desktop.ui.nav import title_for
from smart_space_desktop.ui.pages import build_placeholder_pages
from smart_space_desktop.ui.pages.settings_page import SettingsPage
from smart_space_desktop.ui.sidebar import Sidebar
from smart_space_desktop.ui.topbar import Topbar


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("Smart Space")
        self.setMinimumSize(1100, 700)
        self.resize(1366, 768)

        root = QWidget()
        root.setObjectName("Root")
        root.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # keep initial focus off the first nav button
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.sidebar = Sidebar(ctx)
        h.addWidget(self.sidebar)
        right = QVBoxLayout()
        right.setSpacing(0)
        self.topbar = Topbar(ctx)
        right.addWidget(self.topbar)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        h.addLayout(right, 1)

        self.pages: dict[str, QWidget] = build_placeholder_pages()
        self.pages["settings"] = SettingsPage(ctx)
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.sidebar.navigate.connect(self.navigate)

        # Keyboard shortcuts (requirements §11). Ctrl+digit / Ctrl+, / Ctrl+R never enter text.
        self.shortcuts: dict[str, QShortcut] = {}
        for seq, fn in {
            "Ctrl+1": lambda: self.navigate("dashboard"),
            "Ctrl+2": lambda: self.navigate("rooms"),
            "Ctrl+3": lambda: self.navigate("devices"),
            "Ctrl+4": lambda: self.navigate("commands"),
            "Ctrl+,": lambda: self.navigate("settings"),
            "Ctrl+R": ctx.refresh,
        }.items():
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)
            self.shortcuts[seq] = sc

        self.current_key = ""
        self.navigate("dashboard", animate=False)
        root.setFocus()

    def navigate(self, key: str, *, animate: bool = True) -> None:
        page = self.pages.get(key)
        if page is None or key == self.current_key:
            return
        self.current_key = key
        self.stack.setCurrentWidget(page)
        self.sidebar.set_current(key)
        self.topbar.set_title(title_for(key))
        if animate:
            self._fade_in(page)

    def _fade_in(self, page: QWidget) -> None:
        fx = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", page)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: page.setGraphicsEffect(None))
        anim.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.ctx.shutdown()
        super().closeEvent(event)
