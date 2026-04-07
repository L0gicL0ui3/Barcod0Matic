import os
import sys

# Ensure the app directory is always on sys.path regardless of how the
# script is launched (double-click, Start-Process, IDE, etc.)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app import MainWindow

_STYLESHEET = """
/* ── Global ─────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #1a1a2e;
}
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}

/* ── Header ─────────────────────────────────────────────────────────── */
QLabel#app_header {
    font-size: 26px;
    font-weight: bold;
    color: #FF6B35;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f3460, stop:0.5 #1a1a2e, stop:1 #0f3460);
    border-radius: 10px;
    padding: 10px 0;
    letter-spacing: 4px;
}

/* ── Group Boxes ─────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 8px;
    font-weight: bold;
    font-size: 11px;
    color: #FF6B35;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    left: 14px;
    color: #FF6B35;
    background-color: #1a1a2e;
    border-radius: 4px;
}

/* ── Input Fields ────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #0f3460;
    border: 2px solid #1a4a7a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    font-size: 12px;
    selection-background-color: #9C27B0;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border: 2px solid #00C853;
}
QLineEdit:disabled {
    background-color: #12122a;
    border: 2px solid #252550;
    color: #44446a;
}
QLineEdit:read-only {
    color: #aaaacc;
}

/* ── Buttons – default (orange) ─────────────────────────────────────── */
QPushButton {
    background-color: #FF6B35;
    color: #ffffff;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 12px;
    min-height: 34px;
}
QPushButton:hover {
    background-color: #ff8c5a;
}
QPushButton:pressed {
    background-color: #d9521e;
}
QPushButton:disabled {
    background-color: #252550;
    color: #44446a;
}

/* ── Save button (green) ─────────────────────────────────────────────── */
QPushButton#save_btn {
    background-color: #00C853;
    color: #000000;
}
QPushButton#save_btn:hover {
    background-color: #00e676;
}
QPushButton#save_btn:pressed {
    background-color: #009624;
}
QPushButton#save_btn:disabled {
    background-color: #252550;
    color: #44446a;
}

/* ── Lookup button (purple) ──────────────────────────────────────────── */
QPushButton#lookup_btn {
    background-color: #7B1FA2;
    color: #ffffff;
}
QPushButton#lookup_btn:hover {
    background-color: #9C27B0;
}
QPushButton#lookup_btn:pressed {
    background-color: #5c0f7a;
}
QPushButton#lookup_btn:disabled {
    background-color: #252550;
    color: #44446a;
}

/* ── Labels (read-only record fields) ───────────────────────────────── */
QLabel {
    color: #e0e0e0;
    background: transparent;
}

/* ── Change Log list ─────────────────────────────────────────────────── */
QListWidget {
    background-color: #0f3460;
    border: 2px solid #1a4a7a;
    border-radius: 8px;
    color: #e0e0e0;
    alternate-background-color: #16213e;
    font-size: 11px;
}
QListWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #1a4a7a;
}
QListWidget::item:hover {
    background-color: #1a4a7a;
}
QListWidget::item:selected {
    background-color: #7B1FA2;
    color: #ffffff;
}

/* ── Scrollbars ──────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f3460;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #FF6B35;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Scroll Area ─────────────────────────────────────────────────────── */
QScrollArea {
    background-color: #1a1a2e;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #1a1a2e;
}

/* ── Message/File Dialogs ────────────────────────────────────────────── */
QMessageBox, QFileDialog {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
QMessageBox QLabel {
    color: #e0e0e0;
}
QMessageBox QPushButton {
    min-width: 80px;
}
"""


def main():
    # Required on some Windows + Qt6 combos for HiDPI and input handling
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLESHEET)

    icon_path = os.path.join(_APP_DIR, "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()

    # Auto-load the default data file on startup
    _default_data = os.path.join(_APP_DIR, "UPCDirectory", "UPCdata.csv")
    if os.path.isfile(_default_data):
        window.load_file_path(_default_data)

    window.show()
    window.activateWindow()
    window.raise_()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

