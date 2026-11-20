from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from smart_space_desktop import __version__
from smart_space_desktop.core.connection import ConnectionInfo
from smart_space_desktop.core.context import AppContext
from smart_space_desktop.core.settings import POLL_CHOICES, Settings, validate_base_url
from smart_space_desktop.ui.widgets import Card, repolish


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        s = ctx.settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        col = QVBoxLayout()
        col.setSpacing(16)

        # ---- connection card ----
        card = Card()
        card.setMaximumWidth(720)
        title = QLabel("Connection")
        title.setObjectName("CardTitle")
        card.body.addWidget(title)

        card.body.addWidget(self._muted("Backend URL"))
        self.url = QLineEdit(s.base_url)
        card.body.addWidget(self.url)
        self.url_error = QLabel("")
        self.url_error.setObjectName("Error")
        self.url_error.hide()
        card.body.addWidget(self.url_error)

        card.body.addWidget(self._muted("API token (ss_…)"))
        row = QHBoxLayout()
        self.token = QLineEdit(s.token or "")
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.token, 1)
        self.show_token = QPushButton("Show")
        self.show_token.setObjectName("Secondary")
        self.show_token.setCheckable(True)
        self.show_token.toggled.connect(self._toggle_token)
        row.addWidget(self.show_token)
        card.body.addLayout(row)
        hint = QLabel(
            "The token is stored in Windows Credential Manager. The backend does not issue tokens itself; "
            "paste a token provided by an administrator."
        )
        hint.setObjectName("Small")
        hint.setWordWrap(True)
        card.body.addWidget(hint)

        card.body.addWidget(self._muted("Refresh interval"))
        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.poll_buttons: dict[int, QPushButton] = {}
        for sec in POLL_CHOICES:
            b = QPushButton(f"{sec} s")
            b.setObjectName("Seg")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setChecked(sec == s.poll_seconds)
            self.poll_buttons[sec] = b
            seg.addWidget(b)
        seg.addStretch(1)
        card.body.addLayout(seg)

        self.demo = QCheckBox("Demo Mode — do not send requests to the backend")
        self.demo.setChecked(s.demo_mode)
        card.body.addWidget(self.demo)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(lambda: self.save(check=False))
        self.check_btn = QPushButton("Save and Check")
        self.check_btn.setObjectName("Secondary")
        self.check_btn.clicked.connect(lambda: self.save(check=True))
        btns.addWidget(self.save_btn)
        btns.addWidget(self.check_btn)
        btns.addStretch(1)
        card.body.addLayout(btns)
        self.status = QLabel("")
        self.status.setObjectName("Small")
        card.body.addWidget(self.status)
        col.addWidget(card)

        # ---- diagnostics card ----
        diag = Card()
        diag.setMaximumWidth(720)
        dt = QLabel("Diagnostics")
        dt.setObjectName("CardTitle")
        diag.body.addWidget(dt)
        self.diag_text = QLabel("")
        self.diag_text.setWordWrap(True)
        self.diag_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        diag.body.addWidget(self.diag_text)
        col.addWidget(diag)

        outer.addLayout(col)
        outer.addStretch(1)

        ctx.monitor.changed.connect(self._render_diag)
        self._render_diag(ctx.monitor.info)

    @staticmethod
    def _muted(text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("Muted")
        return l

    def _toggle_token(self, on: bool) -> None:
        self.token.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
        self.show_token.setText("Hide" if on else "Show")

    def selected_poll(self) -> int:
        for sec, b in self.poll_buttons.items():
            if b.isChecked():
                return sec
        return 10

    def validate(self) -> bool:
        ok = validate_base_url(self.url.text())
        self.url.setProperty("invalid", not ok)
        repolish(self.url)
        self.url_error.setText("" if ok else "Enter a URL such as http://host:8000")
        self.url_error.setVisible(not ok)
        return ok

    def save(self, *, check: bool) -> None:
        if not self.validate():
            return
        new = replace(
            self.ctx.settings,
            base_url=self.url.text(),
            token=self.token.text(),
            poll_seconds=self.selected_poll(),
            demo_mode=self.demo.isChecked(),
        )
        self.ctx.store.save(new)  # triggers monitor.restart() which already checks
        self.status.setText("Saved, checking connection…" if check and not new.demo_mode else "Saved")

    def _render_diag(self, info: ConnectionInfo) -> None:
        rows = [("Status", info.state.value)]
        if info.message:
            rows.append(("Message", info.message))
        if info.latency_ms is not None:
            rows.append(("Latency", f"{info.latency_ms} ms"))
        if info.checked_at:
            rows.append(("Checked", info.checked_at.strftime("%Y-%m-%d %H:%M:%S")))
        if info.technical:
            rows.append(("Technical details", info.technical))
        rows.append(("Client version", __version__))
        self.diag_text.setText("<br>".join(f"<span style='color:#91A4B8'>{k}:</span> {v}" for k, v in rows))
