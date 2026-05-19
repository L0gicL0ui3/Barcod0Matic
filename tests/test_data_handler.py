import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

import data_handler


class TestDataHandler(unittest.TestCase):
    def test_normalize_barcode_handles_nan_float_and_string(self):
        self.assertEqual(data_handler._normalize_barcode(float("nan")), "")
        self.assertEqual(data_handler._normalize_barcode(1234567890.0), "1234567890")
        self.assertEqual(data_handler._normalize_barcode(" 00123 "), "00123")

    def test_load_file_normalizes_column1_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "items.csv")
            pd.DataFrame(
                {
                    "Goal": ["A", "B", "C"],
                    "Correct approach": ["X", "Y", "Z"],
                    "Column1": [" 123 ", "00456", ""],
                }
            ).to_csv(path, index=False)

            df = data_handler.load_file(path)

            self.assertEqual(df["Column1"].tolist(), ["123", "00456", ""])

    def test_find_by_barcode_returns_index_or_none(self):
        df = pd.DataFrame({"Column1": ["111", "222"]}, index=[10, 20])
        self.assertEqual(data_handler.find_by_barcode(df, " 222 "), 20)
        self.assertIsNone(data_handler.find_by_barcode(df, "333"))
        self.assertIsNone(data_handler.find_by_barcode(pd.DataFrame({"X": [1]}), "111"))

    def test_update_internal_goal_and_price(self):
        df = pd.DataFrame(
            {
                "Goal": ["Old"],
                "Correct approach": ["ID0"],
                "Column1": ["999"],
            }
        )
        self.assertTrue(data_handler.update_internal_id(df, "999", "ID1"))
        self.assertTrue(data_handler.update_goal(df, "999", "New"))
        self.assertTrue(data_handler.update_price(df, "999", "12.34"))

        self.assertEqual(df.at[0, "Correct approach"], "ID1")
        self.assertEqual(df.at[0, "Goal"], "New")
        self.assertEqual(df.at[0, "Price"], "12.34")

        self.assertFalse(data_handler.update_internal_id(df, "nope", "ID2"))
        self.assertFalse(data_handler.update_goal(df, "nope", "Other"))
        self.assertFalse(data_handler.update_price(df, "nope", "1.00"))

    def test_update_price_creates_missing_column(self):
        df = pd.DataFrame({"Column1": ["111"]})
        self.assertTrue(data_handler.update_price(df, "111", "5.99"))
        self.assertIn("Price", df.columns)
        self.assertEqual(df.at[0, "Price"], "5.99")

    def test_add_row_appends_new_and_skips_duplicates(self):
        df = pd.DataFrame(
            [{"Goal": "A", "Correct approach": "I1", "Column1": "111"}]
        )
        same_df = data_handler.add_row(df, "111", "B", "I2")
        self.assertIs(same_df, df)
        self.assertEqual(len(same_df), 1)

        new_df = data_handler.add_row(df, "222", "B", "I2")
        self.assertEqual(len(new_df), 2)
        self.assertEqual(new_df.iloc[1]["Column1"], "222")
        self.assertEqual(new_df.iloc[1]["Goal"], "B")
        self.assertEqual(new_df.iloc[1]["Correct approach"], "I2")

    def test_save_file_csv_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("old,data\n")

            df = pd.DataFrame({"Column1": ["1"], "Goal": ["G"]})
            data_handler.save_file(df, path)

            saved = pd.read_csv(path, dtype=str)
            self.assertEqual(saved.to_dict(orient="records"), [{"Column1": "1", "Goal": "G"}])

    def test_save_file_csv_creates_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "new.csv")
            df = pd.DataFrame({"Column1": ["7"]})
            data_handler.save_file(df, path)
            self.assertTrue(os.path.isfile(path))

    def test_save_file_csv_permission_error_raises_file_lock_error(self):
        df = pd.DataFrame({"Column1": ["1"]})
        with patch("builtins.open", side_effect=PermissionError("locked")):
            with self.assertRaises(data_handler.FileLockError):
                data_handler.save_file(df, "/tmp/locked.csv")

    def test_save_file_xlsx_permission_error_raises_file_lock_error(self):
        df = MagicMock()
        df.to_excel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.xlsx")
            with patch("os.replace", side_effect=PermissionError("locked")):
                with self.assertRaises(data_handler.FileLockError):
                    data_handler.save_file(df, path)

    def test_generate_barcode_image_uses_code128_and_safe_file_name(self):
        class FakeCode:
            def __init__(self):
                self.saved_path = None
                self.saved_options = None

            def save(self, base_path, options):
                self.saved_path = base_path
                self.saved_options = options
                return base_path + ".png"

        fake_code = FakeCode()
        fake_barcode_module = types.SimpleNamespace(
            get=lambda kind, value, writer: fake_code
        )
        fake_writer_module = types.SimpleNamespace(ImageWriter=type("ImageWriter", (), {}))

        with patch.dict(
            sys.modules,
            {
                "barcode": fake_barcode_module,
                "barcode.writer": fake_writer_module,
            },
        ):
            result = data_handler.generate_barcode_image("abc/123:!*")

        self.assertTrue(result.endswith(".png"))
        self.assertIn("abc_123___", os.path.basename(result))
        self.assertIsNotNone(fake_code.saved_options)
        self.assertEqual(fake_code.saved_options["dpi"], 300)


if __name__ == "__main__":
    unittest.main()
