import re
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class BarcodePreviewDialog(QDialog):
    def __init__(self, barcode_value: str, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Barcode: {barcode_value}")
        self.setMinimumWidth(520)
        self.barcode_value = barcode_value
        self.image_path = image_path
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Barcode value label
        value_lbl = QLabel(self.barcode_value)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_lbl.setStyleSheet(
            "font-family: monospace; font-size: 13px; font-weight: bold; padding: 4px;"
        )
        layout.addWidget(value_lbl)

        # Barcode image preview
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(self.image_path)
        self.img_label.setPixmap(
            pixmap.scaledToWidth(480, Qt.TransformationMode.SmoothTransformation)
        )
        layout.addWidget(self.img_label)

        # Action buttons
        btn_row = QHBoxLayout()

        save_btn = QPushButton("Save as PNG…")
        save_btn.clicked.connect(self._save_png)
        btn_row.addWidget(save_btn)

        print_btn = QPushButton("Print…")
        print_btn.clicked.connect(self._print)
        btn_row.addWidget(print_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _save_png(self):
        safe = re.sub(r"[^\w\-]", "_", self.barcode_value)[:60]
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Barcode Image",
            f"barcode_{safe}.png",
            "PNG Image (*.png)",
        )
        if not path:
            return
        try:
            shutil.copy(self.image_path, path)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _print(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        pixmap = QPixmap(self.image_path)
        painter = QPainter(printer)
        try:
            dpi = printer.resolution()
            # GS1 standard retail barcode physical size: 1.469" wide x 1.020" tall
            target_w = int(1.469 * dpi)
            target_h = int(1.020 * dpi)
            # Center on the page
            page = painter.viewport()
            x = (page.width() - target_w) // 2
            y = (page.height() - target_h) // 2
            painter.drawPixmap(x, y, target_w, target_h, pixmap)
        finally:
            painter.end()
