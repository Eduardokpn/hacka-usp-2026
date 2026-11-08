"""Paleta e folha de estilo."""
from pathlib import Path

CHEVRON = (Path(__file__).parent / "assets" / "chevron.svg").as_posix()

BG = "#F4F6F8"
SURFACE = "#FFFFFF"
INK = "#16181D"
SEC = "#5B6068"
MUTED = "#8A9098"
LINE = "#E3E7EC"
ACCENT = "#0F766E"        # verde-petróleo clínico
ACCENT_HOVER = "#0B5F58"
ACCENT_WASH = "#E6F4F2"
RED = "#E5484D"
GREEN = "#2FB26A"
DARK = "#1C2024"
AMBER = "#B7791F"
AMBER_WASH = "#FFF8E8"

QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    color: {INK};
}}
QMainWindow, #root {{ background: {BG}; }}
QWidget#screen {{ background: {BG}; }}

QLabel#h1 {{ font-size: 26pt; font-weight: 700; letter-spacing: -0.5px; }}
QLabel#sub {{ font-size: 11pt; color: {SEC}; }}
QLabel#eyebrow {{ font-size: 8pt; font-weight: 600; letter-spacing: 1.5px; color: {MUTED}; }}
QLabel#timer {{ font-size: 44pt; font-weight: 300; color: {INK}; }}
QLabel#status {{ font-size: 11pt; color: {SEC}; }}
QLabel#hint {{ font-size: 9pt; color: {MUTED}; }}
QLabel#warn {{
    background: {AMBER_WASH}; color: {AMBER}; border: 1px solid #F1DDB0;
    border-radius: 8px; padding: 8px 14px; font-size: 10pt;
}}
QLabel#error {{ color: {RED}; font-size: 10pt; }}
QLabel#colhead {{ font-size: 8pt; font-weight: 600; letter-spacing: 1.2px; color: {MUTED}; }}
QLabel#fieldname {{ font-size: 12pt; font-weight: 600; }}
QLabel#chip {{
    background: {BG}; color: {SEC}; border-radius: 9px; padding: 2px 9px; font-size: 8pt;
}}
QLabel#emptytag {{
    background: {AMBER_WASH}; color: {AMBER}; border-radius: 9px; padding: 2px 9px; font-size: 8pt;
}}

QFrame#card {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px;
}}
QFrame#card[vazio="true"] {{ border: 1px solid #F1DDB0; border-left: 4px solid {AMBER}; }}
QFrame#row {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px; }}
QFrame#row[erro="true"] {{ border: 1px solid {RED}; }}
QFrame#transcript {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#footer {{ background: {DARK}; }}
QLabel#footertext {{ color: #D7DBDF; font-size: 9pt; letter-spacing: 0.5px; }}

QLineEdit, QPlainTextEdit, QComboBox {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px;
    padding: 7px 10px; font-size: 10.5pt; selection-background-color: {ACCENT_WASH};
    selection-color: {INK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QPlainTextEdit#transcriptText {{ border: none; background: transparent; color: {SEC}; font-size: 10pt; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox::down-arrow {{ image: url("{CHEVRON}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {LINE}; selection-background-color: {ACCENT_WASH};
    selection-color: {INK}; outline: none; padding: 4px;
}}

QPushButton {{
    border-radius: 9px; padding: 9px 18px; font-size: 10.5pt; font-weight: 600;
}}
QPushButton#primary {{ background: {ACCENT}; color: white; border: none; }}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #A9C9C6; }}
QPushButton#secondary {{ background: {SURFACE}; color: {INK}; border: 1px solid {LINE}; }}
QPushButton#secondary:hover {{ border-color: {MUTED}; }}
QPushButton#ghost {{ background: transparent; color: {ACCENT}; border: 1px dashed #9FCFC9; text-align: left; padding: 11px 16px; }}
QPushButton#ghost:hover {{ background: {ACCENT_WASH}; border-style: solid; }}
QPushButton#link {{ background: transparent; color: {ACCENT}; border: none; padding: 4px 6px; font-weight: 600; }}
QPushButton#link:hover {{ text-decoration: underline; }}
QPushButton#link:disabled {{ color: {MUTED}; }}
QTabBar::tab {{ background: transparent; color: {SEC}; padding: 8px 14px; border-bottom: 2px solid {LINE}; }}
QTabBar::tab:hover {{ color: {INK}; }}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; font-weight: 600; }}
QToolButton#rowbtn {{
    background: transparent; border: none; border-radius: 6px; padding: 4px; color: {SEC}; font-size: 11pt;
}}
QToolButton#rowbtn:hover {{ background: {BG}; color: {INK}; }}
QToolButton#rowbtn:disabled {{ color: #CCD1D6; }}
QToolButton#delbtn {{
    background: transparent; border: none; border-radius: 6px; padding: 4px; color: {MUTED}; font-size: 11pt;
}}
QToolButton#delbtn:hover {{ background: #FDECEC; color: {RED}; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CDD3D9; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #AEB5BD; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QMessageBox {{ background: {SURFACE}; }}
QMessageBox QLabel {{ font-size: 10.5pt; }}
QMessageBox QPushButton {{
    background: {SURFACE}; border: 1px solid {LINE}; min-width: 90px; padding: 7px 14px;
}}
QMessageBox QPushButton:hover {{ border-color: {MUTED}; }}
QMessageBox QPushButton:default {{ background: {ACCENT}; color: white; border: none; }}
QToolTip {{ background: {DARK}; color: white; border: none; padding: 5px 8px; border-radius: 4px; }}
"""
