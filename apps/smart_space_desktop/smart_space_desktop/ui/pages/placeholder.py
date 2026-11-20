"""Honest stub: describes what the page will show and where its data will come from.
Never fakes data (requirements §5)."""

from __future__ import annotations

import enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from smart_space_desktop.ui.widgets import Card, StatusChip


class Availability(enum.Enum):
    PLANNED = ("Planned", "info")
    BACKEND_MISSING = ("Unavailable: missing from backend", "warn")
    COMING_SOON = ("Coming Soon", "info")


class PlaceholderPage(QWidget):
    def __init__(
        self, title: str, description: str, source: str, availability: Availability
    ) -> None:
        super().__init__()
        self.setObjectName("Page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = Card(glow=True)
        card.setMaximumWidth(720)
        head = QHBoxLayout()
        t = QLabel(title)
        t.setObjectName("CardTitle")
        head.addWidget(t, 1)
        label, tone = availability.value
        chip = StatusChip()
        chip.setText(label)
        chip.setProperty("tone", tone)
        head.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
        card.body.addLayout(head)

        desc = QLabel(description)
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        card.body.addWidget(desc)
        src = QLabel(f"Data source: {source}")
        src.setObjectName("Small")
        src.setWordWrap(True)
        card.body.addWidget(src)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
        outer.addStretch(1)
