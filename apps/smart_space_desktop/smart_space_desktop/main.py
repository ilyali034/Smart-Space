from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from smart_space_desktop.core.context import AppContext
from smart_space_desktop.core.settings import KeyringTokenStore, SettingsStore
from smart_space_desktop.ui.main_window import MainWindow
from smart_space_desktop.ui.theme import apply_theme


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setOrganizationName("SmartSpace")
    app.setApplicationName("SmartSpaceDesktop")
    apply_theme(app)

    store = SettingsStore(QSettings(), KeyringTokenStore())
    ctx = AppContext(store)
    window = MainWindow(ctx)
    window.show()
    ctx.start()
    return app.exec()
