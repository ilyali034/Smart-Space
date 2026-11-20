"""All colors live here (requirements §4.2)."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class C:
    BACKGROUND = "#080D16"
    SIDEBAR = "#0D1420"
    CARD = "#111D2B"
    SURFACE = "#172638"
    ACCENT = "#35C8F4"
    ACCENT2 = "#668CFF"
    SUCCESS = "#35D39A"
    WARNING = "#FFB84D"
    DANGER = "#FF5F6D"
    TEXT = "#EAF4FF"
    TEXT2 = "#91A4B8"
    BORDER = "#26394C"


QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 14px; color: {C.TEXT}; }}
QMainWindow, QWidget#Root, QWidget#Page {{ background: {C.BACKGROUND}; }}
QToolTip {{ background: {C.SURFACE}; color: {C.TEXT}; border: 1px solid {C.BORDER}; padding: 4px 8px; }}

QFrame#Sidebar {{ background: {C.SIDEBAR}; border-right: 1px solid {C.BORDER}; }}
QLabel#Logo {{ font-size: 15px; font-weight: 700; letter-spacing: 2px; color: {C.TEXT}; }}
QLabel#SideInfo {{ font-size: 11px; color: {C.TEXT2}; }}
QLabel#SideInfo[demo="true"] {{ color: {C.WARNING}; font-weight: 600; }}
QPushButton#Nav {{
    text-align: left; padding: 11px 14px; border: none; border-left: 3px solid transparent;
    border-radius: 8px; background: transparent; color: {C.TEXT2};
}}
QPushButton#Nav:hover {{ background: rgba(53,200,244,0.08); color: {C.TEXT}; }}
QPushButton#Nav:checked {{
    background: rgba(53,200,244,0.14); color: {C.TEXT}; font-weight: 600;
    border-left: 3px solid {C.ACCENT};
}}
QPushButton#Nav:focus {{ border: 1px solid rgba(53,200,244,0.45); }}

QFrame#Topbar {{ background: transparent; border-bottom: 1px solid {C.BORDER}; }}
QLabel#Title {{ font-size: 20px; font-weight: 600; }}
QLabel#DemoBadge {{
    color: {C.WARNING}; border: 1px solid {C.WARNING}; border-radius: 6px;
    padding: 4px 10px; font-weight: 700; letter-spacing: 1px; font-size: 12px;
    background: rgba(255,184,77,0.12);
}}
QLabel#Chip {{ border-radius: 12px; padding: 4px 12px; font-size: 12px; border: 1px solid {C.BORDER}; }}
QLabel#Chip[tone="ok"] {{ color: {C.SUCCESS}; border-color: {C.SUCCESS}; background: rgba(53,211,154,0.10); }}
QLabel#Chip[tone="warn"] {{ color: {C.WARNING}; border-color: {C.WARNING}; background: rgba(255,184,77,0.10); }}
QLabel#Chip[tone="danger"] {{ color: {C.DANGER}; border-color: {C.DANGER}; background: rgba(255,95,109,0.10); }}
QLabel#Chip[tone="info"] {{ color: {C.ACCENT}; border-color: {C.ACCENT}; background: rgba(53,200,244,0.10); }}
QLabel#Chip[tone="muted"] {{ color: {C.TEXT2}; }}
QToolButton#TopBtn {{ border: none; padding: 6px 10px; color: {C.TEXT2}; border-radius: 6px; }}
QToolButton#TopBtn:hover {{ background: rgba(53,200,244,0.10); color: {C.TEXT}; }}
QToolButton#TopBtn:disabled {{ color: {C.BORDER}; }}
QLabel#Avatar {{ background: {C.SURFACE}; border-radius: 15px; color: {C.TEXT2}; }}

QFrame#Card {{ background: {C.CARD}; border: 1px solid {C.BORDER}; border-radius: 14px; }}
QFrame#Card[glow="true"] {{ border: 1px solid rgba(53,200,244,0.47); }}
QLabel#CardTitle {{ font-size: 18px; font-weight: 600; }}
QLabel#Muted {{ color: {C.TEXT2}; }}
QLabel#Small {{ color: {C.TEXT2}; font-size: 12px; }}
QLabel#Error {{ color: {C.DANGER}; font-size: 12px; }}

QLineEdit {{
    background: {C.SURFACE}; border: 1px solid {C.BORDER}; border-radius: 8px; padding: 6px 12px; min-height: 24px;
    selection-background-color: {C.ACCENT}; selection-color: {C.BACKGROUND};
}}
QLineEdit:focus {{ border: 1px solid {C.ACCENT}; }}
QLineEdit[invalid="true"] {{ border: 1px solid {C.DANGER}; }}
QPushButton#Primary {{
    background: {C.ACCENT}; color: {C.BACKGROUND}; border: none; border-radius: 8px;
    padding: 6px 18px; min-height: 24px; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: #5AD6F8; }}
QPushButton#Primary:disabled {{ background: {C.BORDER}; color: {C.TEXT2}; }}
QPushButton#Secondary {{
    background: transparent; border: 1px solid {C.BORDER}; border-radius: 8px; padding: 6px 18px; min-height: 24px;
}}
QPushButton#Secondary:hover {{ border-color: {C.ACCENT}; }}
QPushButton#Secondary:disabled {{ color: {C.TEXT2}; }}
QPushButton#Seg {{
    background: {C.SURFACE}; border: 1px solid {C.BORDER}; padding: 5px 16px; min-height: 24px; border-radius: 0;
}}
QPushButton#Seg:checked {{ background: rgba(53,200,244,0.20); border-color: {C.ACCENT}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {C.BORDER}; border-radius: 4px; background: {C.SURFACE}; }}
QCheckBox::indicator:checked {{ background: {C.ACCENT}; border-color: {C.ACCENT}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {C.BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C.BACKGROUND))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(C.SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(C.SURFACE))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C.TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C.ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C.BACKGROUND))
    app.setPalette(pal)
    app.setStyleSheet(QSS)
