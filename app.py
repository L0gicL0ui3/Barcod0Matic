import os
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import urllib.error

import data_handler as dh
from barcode_dialog import BarcodePreviewDialog
from data_handler import FileLockError
import upc_lookup


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df = None
        self.file_path = None
        self._current_barcode = ""
        self._build_ui()
        # Set window icon so it shows in the taskbar and title bar
        _here = os.path.dirname(os.path.abspath(__file__))
        _ico = os.path.join(_here, "icon.ico")
        if os.path.isfile(_ico):
            self.setWindowIcon(QIcon(_ico))
        # Timer to auto-clear status messages after 6 s
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self._set_status("", "black"))

    def _build_ui(self):
        self.setWindowTitle("BarcodOmatic")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # Header — always visible above the scroll area
        header = QLabel("BarcodOmatic")
        header.setObjectName("app_header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(header)

        # Scrollable main area — shows scrollbars when window is small,
        # expands all groups when window is large
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, stretch=1)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setSpacing(12)
        root.setContentsMargins(16, 12, 16, 12)

        # File section
        file_group = QGroupBox("Data File")
        file_layout = QHBoxLayout(file_group)
        self.file_label = QLabel("No file loaded — click Browse to open your CSV or Excel file")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label, 1)
        self.load_btn = QPushButton("Browse...")
        self.load_btn.setObjectName("load_btn")
        self.load_btn.setFixedWidth(90)
        self.load_btn.clicked.connect(self._load_file)
        file_layout.addWidget(self.load_btn)
        root.addWidget(file_group)

        # Scan section
        scan_group = QGroupBox("Barcode Scan")
        scan_layout = QFormLayout(scan_group)
        scan_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan or type barcode, then press Enter")
        self.barcode_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.barcode_input.setClearButtonEnabled(True)
        self.barcode_input.returnPressed.connect(self._on_barcode_entered)
        scan_layout.addRow("Barcode:", self.barcode_input)
        self.lookup_btn = QPushButton("Look Up Online")
        self.lookup_btn.setObjectName("lookup_btn")
        self.lookup_btn.setEnabled(False)
        self.lookup_btn.setToolTip("Search Open Food Facts (free/unlimited) then UPCitemdb (100/day) for this barcode")
        self.lookup_btn.clicked.connect(self._lookup_online)
        scan_layout.addRow("", self.lookup_btn)
        root.addWidget(scan_group)

        # Matched record
        match_group = QGroupBox("Matched Record")
        match_layout = QFormLayout(match_group)
        match_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.lbl_goal = QLabel("—")
        self.lbl_current_id = QLabel("—")
        self.lbl_barcode_matched = QLabel("—")
        self.lbl_price = QLabel("—")
        for lbl in (self.lbl_goal, self.lbl_current_id, self.lbl_barcode_matched, self.lbl_price):
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        match_layout.addRow("Goal:", self.lbl_goal)
        match_layout.addRow("Current Internal ID:", self.lbl_current_id)
        match_layout.addRow("Barcode (Column1):", self.lbl_barcode_matched)
        match_layout.addRow("Price:", self.lbl_price)
        self.print_btn = QPushButton("Generate && Print Barcode...")
        self.print_btn.setObjectName("print_btn")
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self._print_barcode)
        match_layout.addRow(self.print_btn)
        root.addWidget(match_group)


        # Update section
        update_group = QGroupBox("Update Product")
        update_outer = QVBoxLayout(update_group)

        prefix_row = QHBoxLayout()
        prefix_row.addWidget(QLabel("ID Prefix:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("ITEM-")
        self.prefix_input.setFixedWidth(100)
        self.prefix_input.setToolTip("Prefix prepended to the barcode to form the auto-generated ID")
        prefix_row.addWidget(self.prefix_input)
        prefix_row.addStretch()
        update_outer.addLayout(prefix_row)

        update_form = QFormLayout()
        update_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.new_goal_input = QLineEdit()
        self.new_goal_input.setPlaceholderText("Product name / description")
        self.new_goal_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.new_goal_input.setClearButtonEnabled(True)
        self.new_goal_input.setEnabled(False)
        self.new_goal_input.returnPressed.connect(self._save_change)
        update_form.addRow("Product Name:", self.new_goal_input)

        self.new_id_input = QLineEdit()
        self.new_id_input.setPlaceholderText("Auto-filled from barcode — edit if needed")
        self.new_id_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.new_id_input.setClearButtonEnabled(True)
        self.new_id_input.setEnabled(False)
        self.new_id_input.returnPressed.connect(self._save_change)
        update_form.addRow("Internal ID:", self.new_id_input)

        self.new_price_input = QLineEdit()
        self.new_price_input.setPlaceholderText("e.g. 4.99")
        self.new_price_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.new_price_input.setClearButtonEnabled(True)
        self.new_price_input.setEnabled(False)
        self.new_price_input.returnPressed.connect(self._save_change)
        update_form.addRow("Price ($):", self.new_price_input)

        update_outer.addLayout(update_form)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_change)
        update_outer.addWidget(self.save_btn)
        root.addWidget(update_group)

        # Change log — expands to fill available space when window is resized
        log_group = QGroupBox("Change Log (this session)")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(80)
        self.log_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        log_layout.addWidget(self.log_list)
        root.addWidget(log_group, stretch=1)

        # Status bar — outside the scroll area so it's always visible
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(28)
        outer.addWidget(self.status_label)

        # Ctrl+O shortcut to open file
        qs = QShortcut(QKeySequence("Ctrl+O"), self)
        qs.activated.connect(self._load_file)

        self.barcode_input.setFocus()

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self.save_btn.isEnabled():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Discard them and quit?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        event.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, msg, color="black"):
        palette = {
            "green": "#00E676",
            "red": "#FF5252",
            "blue": "#40C4FF",
            "orange": "#FF6D00",
            "black": "#E0E0E0",
        }
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(
            f"color: {palette.get(color, '#E0E0E0')}; font-weight: bold; padding: 4px;"
        )
        # Auto-clear non-error messages after 6 seconds
        if msg and color in ("green", "blue", "black"):
            self._status_timer.start(6000)
        else:
            self._status_timer.stop()

    def _clear_match(self):
        self.lbl_goal.setText("—")
        self.lbl_current_id.setText("—")
        self.lbl_barcode_matched.setText("—")
        self.lbl_price.setText("—")
        self.print_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.new_id_input.setEnabled(False)
        self.new_id_input.clear()
        self.new_goal_input.setEnabled(False)
        self.new_goal_input.clear()
        self.new_price_input.setEnabled(False)
        self.new_price_input.clear()
        self._current_barcode = ""
        self.lookup_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def load_file_path(self, path: str):
        """Load a file directly by path (used by main.py for auto-loading on startup)."""
        try:
            self.df = dh.load_file(path)
            self.file_path = path
            self.file_label.setText(path)
            self._set_status(
                f"Loaded {len(self.df)} rows. Scan or type a barcode to look up a record.",
                "green",
            )
        except Exception as exc:
            self.file_label.setText(f"Failed to load: {path}")
            self._set_status(str(exc), "red")

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSV or Excel File",
            "",
            "Data files (*.csv *.xlsx *.xls);;All files (*)",
        )
        if not path:
            return
        try:
            self.df = dh.load_file(path)
            self.file_path = path
            self.file_label.setText(path)
            self._set_status(
                f"Loaded {len(self.df)} rows. Scan or type a barcode to look up a record.",
                "green",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", str(exc))
            return
        self._clear_match()
        self.barcode_input.setFocus()

    def _on_barcode_entered(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        if self.df is None:
            self._set_status("No file loaded. Click Browse first.", "orange")
            return
        idx = dh.find_by_barcode(self.df, barcode)
        if idx is None:
            self._clear_match()
            self._current_barcode = barcode  # keep for lookup_online
            self.lookup_btn.setEnabled(True)
            self._set_status(
                f"Not in file: {barcode}  —  click 'Look Up Online' to search Open Food Facts / UPCitemdb.",
                "orange",
            )
            return
        self._current_barcode = barcode
        row = self.df.loc[idx]
        self.lbl_goal.setText(str(row.get("Goal", "—")))
        self.lbl_current_id.setText(str(row.get("Correct approach", "—")))
        self.lbl_barcode_matched.setText(str(row.get("Column1", barcode)))
        price_val = str(row.get("Price", "")) if "Price" in self.df.columns else ""
        self.lbl_price.setText(price_val if price_val and price_val != "nan" else "—")
        self.save_btn.setEnabled(True)
        self.print_btn.setEnabled(True)
        self.lookup_btn.setEnabled(False)
        self.new_id_input.setEnabled(True)
        self.new_goal_input.setEnabled(True)
        self.new_price_input.setEnabled(True)
        # Auto-fill fields from matched record
        self.new_goal_input.setText(str(row.get("Goal", "")))
        self.new_price_input.setText(price_val if price_val and price_val != "nan" else "")
        # Auto-fill new ID as prefix + barcode
        prefix = self.prefix_input.text().strip()
        self.new_id_input.setText(f"{prefix}{barcode}")
        self.new_id_input.selectAll()  # selected so user can type over it instantly
        self.new_id_input.setFocus()
        self._set_status(
            "Record found. Edit product name, price and/or internal ID, then Save Changes.",
            "blue",
        )

    def _save_change(self):
        if self.df is None:
            self._set_status("No file loaded.", "orange")
            return
        if not self._current_barcode:
            self._set_status("No barcode selected. Scan a barcode first.", "orange")
            return
        new_id = self.new_id_input.text().strip()
        new_goal = self.new_goal_input.text().strip()
        new_price = self.new_price_input.text().strip()
        if not new_id:
            self._set_status("Internal ID cannot be empty.", "red")
            self.new_id_input.setFocus()
            return
        # Validate price — must be empty or a positive decimal number
        if new_price:
            try:
                price_val = float(new_price.replace(",", ".").lstrip("$"))
                if price_val < 0:
                    raise ValueError
                new_price = f"{price_val:.2f}"
            except ValueError:
                self._set_status("Price must be a number (e.g. 4.99). Leave blank to clear.", "red")
                self.new_price_input.setFocus()
                return
        # Warn if the new internal ID already belongs to a different barcode
        if "Correct approach" in self.df.columns:
            dup = self.df[
                (self.df["Correct approach"] == new_id) &
                (self.df["Column1"] != self._current_barcode)
            ]
            if not dup.empty:
                other_bc = dup.iloc[0].get("Column1", "unknown")
                reply = QMessageBox.warning(
                    self,
                    "Duplicate Internal ID",
                    f"The ID '{new_id}' is already assigned to barcode '{other_bc}'.\n\nSave anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.new_id_input.setFocus()
                    return
        old_id = self.lbl_current_id.text()
        old_goal = self.lbl_goal.text()
        old_price = self.lbl_price.text()
        dh.update_goal(self.df, self._current_barcode, new_goal)
        dh.update_price(self.df, self._current_barcode, new_price)
        success = dh.update_internal_id(self.df, self._current_barcode, new_id)
        if not success:
            self._set_status("Save failed: barcode no longer found in data.", "red")
            return
        try:
            dh.save_file(self.df, self.file_path)
        except FileLockError as exc:
            new_path = self._save_as_fallback(str(exc))
            if not new_path:
                return
            self.file_path = new_path
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        changes = []
        if new_goal != old_goal:
            changes.append(f"name: '{old_goal}' -> '{new_goal}'")
        if new_id != old_id:
            changes.append(f"ID: '{old_id}' -> '{new_id}'")
        if new_price != old_price and not (new_price == "" and old_price == "—"):
            changes.append(f"price: '{old_price}' -> '{new_price}'")
        log_entry = f"[{timestamp}]  {self._current_barcode}  |  " + ("  ".join(changes) if changes else "no changes")
        self.log_list.insertItem(0, log_entry)
        self.lbl_goal.setText(new_goal)
        self.lbl_current_id.setText(new_id)
        self.lbl_price.setText(new_price or "—")
        self._set_status(f"Saved changes for {self._current_barcode}", "green")
        self.barcode_input.clear()
        self.new_id_input.clear()
        self.new_id_input.setEnabled(False)
        self.new_goal_input.clear()
        self.new_goal_input.setEnabled(False)
        self.new_price_input.clear()
        self.new_price_input.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.lookup_btn.setEnabled(False)
        # Keep print_btn enabled so user can still print the barcode
        self.barcode_input.setFocus()

    def _lookup_online(self):
        barcode = self._current_barcode or self.barcode_input.text().strip()
        if not barcode:
            return
        self._set_status("Looking up barcode online (Open Food Facts → UPCitemdb)...", "blue")
        try:
            result = upc_lookup.lookup_upc(barcode)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                self._set_status(
                    "UPCitemdb rate limit reached (100/day). Open Food Facts also had no result.", "red"
                )
            else:
                self._set_status(f"Lookup failed: HTTP {exc.code}", "red")
            return
        except Exception as exc:
            self._set_status(f"Lookup error: {exc}", "red")
            return

        if result is None:
            self._set_status(f"Not found in Open Food Facts or UPCitemdb: {barcode}", "red")
            return

        title = result["title"]
        brand = result["brand"]
        model = result["model"]
        source = result.get("source", "online")
        display = title
        if brand and brand not in title:
            display = f"{brand} - {title}"

        if self.df is None:
            self._set_status("Load a file first before adding a new product.", "orange")
            return

        reply = QMessageBox.question(
            self,
            "Product Found — Add to CSV?",
            f"Product: {display}\nModel: {model}\nSource: {source}\n\nAdd this barcode to your CSV file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Assign a unique auto-incremented internal ID (finds max existing ITEM-N)
        existing_ids = self.df["Correct approach"].dropna().tolist() if "Correct approach" in self.df.columns else []
        max_n = 0
        import re as _re
        for eid in existing_ids:
            m = _re.fullmatch(r"ITEM-0*(\d+)", str(eid).strip())
            if m:
                max_n = max(max_n, int(m.group(1)))
        new_id = f"ITEM-{max_n + 1:04d}"

        self.df = dh.add_row(self.df, barcode, display, new_id)
        try:
            dh.save_file(self.df, self.file_path)
        except FileLockError as exc:
            new_path = self._save_as_fallback(str(exc))
            if not new_path:
                return
            self.file_path = new_path
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_list.insertItem(0, f"[{timestamp}]  ADDED  {barcode}  |  '{display}'  ->  '{new_id}'")

        # Show the newly added record
        self.lbl_goal.setText(display)
        self.lbl_current_id.setText(new_id)
        self.lbl_barcode_matched.setText(barcode)
        self.lbl_price.setText("—")
        self.save_btn.setEnabled(True)
        self.print_btn.setEnabled(True)
        self.new_id_input.setEnabled(True)
        self.new_goal_input.setEnabled(True)
        self.new_goal_input.setText(display)
        self.new_price_input.setEnabled(True)
        self.new_price_input.clear()
        self.lookup_btn.setEnabled(False)
        self._set_status(
            f"Added to CSV [{source}]: '{display}' with ID '{new_id}'", "green"
        )

    def _save_as_fallback(self, lock_msg: str) -> str | None:
        """Show a Save As dialog when the original file is locked.

        Saves to the chosen path and returns it (updating self.file_path),
        or returns None if the user cancels.
        """
        import os
        from pathlib import Path
        btn = QMessageBox.warning(
            self,
            "File Locked — Save As?",
            f"{lock_msg}\n\nWould you like to save to a different file instead?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if btn != QMessageBox.StandardButton.Yes:
            return None

        orig = self.file_path or ""
        ext = Path(orig).suffix or ".csv"
        stem = Path(orig).stem
        suggested = os.path.join(os.path.expanduser("~"), "Desktop", f"{stem}_saved{ext}")

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            suggested,
            "Data files (*.csv *.xlsx *.xls);;All files (*)",
        )
        if not path:
            return None

        try:
            dh.save_file(self.df, path)
            self.file_label.setText(path)
            self._set_status(f"Saved to: {path}", "green")
            return path
        except Exception as exc:
            QMessageBox.critical(self, "Save As Error", str(exc))
            return None

    def _print_barcode(self):
        barcode_value = self._current_barcode or self.barcode_input.text().strip()
        if not barcode_value:
            self._set_status("No barcode to generate. Scan a barcode first.", "orange")
            return
        try:
            image_path = dh.generate_barcode_image(barcode_value)
            dlg = BarcodePreviewDialog(barcode_value, image_path, self)
            dlg.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Barcode Generation Error", str(exc))
