from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from smart_space_desktop.ui.theme import C


def repolish(w: QWidget) -> None:
    """Re-apply QSS after a dynamic property changed."""
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, *, glow: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setProperty("glow", glow)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(22, 20, 22, 20)
        self.body.setSpacing(10)
        if glow:
            fx = QGraphicsDropShadowEffect(self)
            fx.setBlurRadius(28)
            fx.setOffset(0, 0)
            c = QColor(C.ACCENT)
            c.setAlpha(60)
            fx.setColor(c)
            self.setGraphicsEffect(fx)


class StatusChip(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Chip")
        self.set_status("Checking…", "muted")

    def set_status(self, text: str, tone: str) -> None:
        self.setText(f"●  {text}")
        self.setProperty("tone", tone)
        repolish(self)
