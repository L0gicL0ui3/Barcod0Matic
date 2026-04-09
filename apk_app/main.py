import csv
import json
import os
import re
import tempfile
import threading
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from kivy.app import App
from kivy.clock import mainthread
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


OFF_URL = "https://world.openfoodfacts.org/api/v0/product/{upc}.json"
UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"


class BarcodOmaticMobile(BoxLayout):
    status_text = StringProperty("Ready")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=8, padding=10, **kwargs)

        self.records = []
        self.file_path = ""
        self.current_barcode = ""

        self._build_ui()

    def _build_ui(self):
        self.add_widget(Label(text="BarcodOmatic Mobile", font_size="22sp", size_hint_y=None, height=40))

        self.file_label = Label(text="Data file: not loaded", size_hint_y=None, height=30)
        self.add_widget(self.file_label)

        top_buttons = BoxLayout(size_hint_y=None, height=42, spacing=8)
        load_btn = Button(text="Load CSV")
        load_btn.bind(on_press=lambda *_: self.load_default_csv())
        save_btn = Button(text="Save")
        save_btn.bind(on_press=lambda *_: self.save_csv())
        top_buttons.add_widget(load_btn)
        top_buttons.add_widget(save_btn)
        self.add_widget(top_buttons)

        self.barcode_input = TextInput(hint_text="Scan or type barcode", multiline=False, size_hint_y=None, height=40)
        self.add_widget(self.barcode_input)

        scan_buttons = BoxLayout(size_hint_y=None, height=42, spacing=8)
        find_btn = Button(text="Find")
        find_btn.bind(on_press=lambda *_: self.on_find_barcode())
        lookup_btn = Button(text="Look Up Online")
        lookup_btn.bind(on_press=lambda *_: self.lookup_online())
        scan_buttons.add_widget(find_btn)
        scan_buttons.add_widget(lookup_btn)
        self.add_widget(scan_buttons)

        form_scroll = ScrollView(size_hint=(1, 1))
        form = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        self.goal_input = TextInput(hint_text="Product name", multiline=False, size_hint_y=None, height=40)
        self.internal_id_input = TextInput(hint_text="Internal ID", multiline=False, size_hint_y=None, height=40)
        self.price_input = TextInput(hint_text="Price (example: 4.99)", multiline=False, size_hint_y=None, height=40)

        form.add_widget(Label(text="Product Name", size_hint_y=None, height=24))
        form.add_widget(self.goal_input)
        form.add_widget(Label(text="Internal ID", size_hint_y=None, height=24))
        form.add_widget(self.internal_id_input)
        form.add_widget(Label(text="Price", size_hint_y=None, height=24))
        form.add_widget(self.price_input)

        action_buttons = BoxLayout(size_hint_y=None, height=42, spacing=8)
        apply_btn = Button(text="Save Changes")
        apply_btn.bind(on_press=lambda *_: self.apply_changes())
        barcode_btn = Button(text="Generate Barcode PNG")
        barcode_btn.bind(on_press=lambda *_: self.generate_barcode_png())
        action_buttons.add_widget(apply_btn)
        action_buttons.add_widget(barcode_btn)
        form.add_widget(action_buttons)

        form_scroll.add_widget(form)
        self.add_widget(form_scroll)

        self.status_label = Label(text=self.status_text, size_hint_y=None, height=30)
        self.add_widget(self.status_label)

    @mainthread
    def set_status(self, msg):
        self.status_text = msg
        self.status_label.text = msg

    @mainthread
    def _apply_online_result(self, barcode, result):
        title = result.get("title", "")
        brand = result.get("brand", "")
        display = f"{brand} - {title}" if brand and brand.lower() not in title.lower() else title

        self.current_barcode = barcode
        self.goal_input.text = display.strip()
        self.internal_id_input.text = f"ITEM-{self.next_item_id():04d}"
        self.price_input.text = ""
        self.set_status(f"Online result found from {result.get('source', 'online')}")

    @staticmethod
    def normalize_barcode(value):
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if "e" in text.lower():
            try:
                return str(int(Decimal(text)))
            except (InvalidOperation, ValueError):
                return text
        if text.endswith(".0"):
            try:
                return str(int(float(text)))
            except ValueError:
                return text
        return text

    def default_csv_path(self):
        app = App.get_running_app()
        return os.path.join(app.user_data_dir, "UPCdata.csv")

    def load_default_csv(self):
        path = self.default_csv_path()
        if not os.path.exists(path):
            self.records = []
            self.file_path = path
            self.file_label.text = f"Data file: {path} (new file)"
            self.set_status("No CSV found. A new one will be created on first save.")
            return

        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.records = list(reader)

        for row in self.records:
            row["Column1"] = self.normalize_barcode(row.get("Column1", ""))
            row.setdefault("Goal", "")
            row.setdefault("Correct approach", "")
            row.setdefault("Price", "")

        self.file_path = path
        self.file_label.text = f"Data file: {path}"
        self.set_status(f"Loaded {len(self.records)} records")

    def save_csv(self):
        if not self.file_path:
            self.file_path = self.default_csv_path()

        headers = ["Goal", "Correct approach", "Column1", "Price"]
        for row in self.records:
            for key in row.keys():
                if key not in headers:
                    headers.append(key)

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(self.records)
        self.set_status(f"Saved {len(self.records)} records")

    def find_record_index(self, barcode):
        barcode = self.normalize_barcode(barcode)
        for i, row in enumerate(self.records):
            if self.normalize_barcode(row.get("Column1", "")) == barcode:
                return i
        return None

    def on_find_barcode(self):
        barcode = self.normalize_barcode(self.barcode_input.text)
        if not barcode:
            self.set_status("Enter a barcode first")
            return

        idx = self.find_record_index(barcode)
        if idx is None:
            self.current_barcode = barcode
            self.goal_input.text = ""
            self.internal_id_input.text = f"ITEM-{self.next_item_id():04d}"
            self.price_input.text = ""
            self.set_status("Barcode not found. Use Look Up Online or enter data manually.")
            return

        row = self.records[idx]
        self.current_barcode = barcode
        self.goal_input.text = row.get("Goal", "")
        self.internal_id_input.text = row.get("Correct approach", "")
        self.price_input.text = row.get("Price", "")
        self.set_status("Record found")

    def validate_price(self, value):
        text = (value or "").strip()
        if not text:
            return ""
        try:
            parsed = float(text.replace(",", ".").lstrip("$"))
            if parsed < 0:
                return None
            return f"{parsed:.2f}"
        except ValueError:
            return None

    def apply_changes(self):
        barcode = self.normalize_barcode(self.current_barcode or self.barcode_input.text)
        if not barcode:
            self.set_status("Scan or enter a barcode before saving")
            return

        new_goal = self.goal_input.text.strip()
        new_id = self.internal_id_input.text.strip()
        normalized_price = self.validate_price(self.price_input.text)

        if not new_id:
            self.set_status("Internal ID is required")
            return
        if normalized_price is None:
            self.set_status("Price must be numeric, for example 4.99")
            return

        idx = self.find_record_index(barcode)
        if idx is None:
            self.records.append(
                {
                    "Goal": new_goal,
                    "Correct approach": new_id,
                    "Column1": barcode,
                    "Price": normalized_price,
                }
            )
        else:
            self.records[idx]["Goal"] = new_goal
            self.records[idx]["Correct approach"] = new_id
            self.records[idx]["Column1"] = barcode
            self.records[idx]["Price"] = normalized_price

        self.current_barcode = barcode
        self.save_csv()

    def next_item_id(self):
        max_id = 0
        for row in self.records:
            val = str(row.get("Correct approach", "")).strip()
            m = re.fullmatch(r"ITEM-0*(\d+)", val)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    def lookup_online(self):
        barcode = self.normalize_barcode(self.current_barcode or self.barcode_input.text)
        if not barcode:
            self.set_status("Enter a barcode first")
            return

        self.set_status("Looking up product online...")
        threading.Thread(target=self._lookup_online_worker, args=(barcode,), daemon=True).start()

    def _lookup_online_worker(self, barcode):
        result = self._lookup_open_food_facts(barcode)
        if result is None:
            result = self._lookup_upcitemdb(barcode)

        if result is None:
            self.set_status("No online result for this barcode")
            return

        self._apply_online_result(barcode, result)

    def _lookup_open_food_facts(self, upc):
        url = OFF_URL.format(upc=upc)
        try:
            response = urlopen(url, timeout=10)
            payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError):
            return None

        product = payload.get("product") or {}
        title = (product.get("product_name") or "").strip()
        brand = (product.get("brands") or "").split(",")[0].strip()
        if not title:
            return None

        return {
            "title": title,
            "brand": brand,
            "source": "Open Food Facts",
        }

    def _lookup_upcitemdb(self, upc):
        url = UPCITEMDB_URL.format(upc=upc)
        try:
            response = urlopen(url, timeout=10)
            payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError):
            return None

        items = payload.get("items") or []
        if not items:
            return None

        item = items[0]
        return {
            "title": (item.get("title") or "").strip(),
            "brand": (item.get("brand") or "").strip(),
            "source": "UPCitemdb",
        }

    def generate_barcode_png(self):
        barcode_value = self.normalize_barcode(self.current_barcode or self.barcode_input.text)
        if not barcode_value:
            self.set_status("No barcode to generate")
            return

        try:
            import barcode as bc
            from barcode.writer import ImageWriter

            tmp_dir = tempfile.mkdtemp(prefix="barcode_mobile_")
            out_base = os.path.join(tmp_dir, f"{barcode_value}")
            code = bc.get("code128", barcode_value, writer=ImageWriter())
            image_path = code.save(
                out_base,
                options={
                    "module_width": 0.33,
                    "module_height": 22.85,
                    "quiet_zone": 6.5,
                    "font_size": 10,
                    "text_distance": 5.0,
                    "dpi": 300,
                },
            )
        except Exception as exc:
            self.set_status(f"Barcode generation failed: {exc}")
            return

        image = Image(source=image_path, allow_stretch=True)
        popup = Popup(title="Generated Barcode", content=image, size_hint=(0.9, 0.6))
        popup.open()
        self.set_status(f"Barcode image saved to {image_path}")


class BarcodOmaticMobileApp(App):
    def build(self):
        return BarcodOmaticMobile()


if __name__ == "__main__":
    BarcodOmaticMobileApp().run()
