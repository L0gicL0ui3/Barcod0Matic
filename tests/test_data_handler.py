"""Tests for data_handler.py."""
import io
import math
import os
import sys
import tempfile
import unittest
import unittest.mock

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import data_handler


# ---------------------------------------------------------------------------
# Helper: build a standard test DataFrame
# ---------------------------------------------------------------------------

def _make_df(rows=None):
    """Return a DataFrame with the columns used by the app."""
    if rows is None:
        rows = [
            {"Column1": "111", "Goal": "Apple", "Correct approach": "A001", "Price": "1.99"},
            {"Column1": "222", "Goal": "Banana", "Correct approach": "B002", "Price": "0.50"},
            {"Column1": "333", "Goal": "Cherry", "Correct approach": "C003", "Price": "3.00"},
        ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# _normalize_barcode
# ---------------------------------------------------------------------------

class TestNormalizeBarcode(unittest.TestCase):

    def test_nan_returns_empty_string(self):
        self.assertEqual(data_handler._normalize_barcode(float("nan")), "")

    def test_float_returns_int_string(self):
        # Excel stores 194846000000 as 1.94846e+11
        self.assertEqual(data_handler._normalize_barcode(194846000000.0), "194846000000")

    def test_plain_string_is_stripped(self):
        self.assertEqual(data_handler._normalize_barcode("  012345  "), "012345")

    def test_integer_string_unchanged(self):
        self.assertEqual(data_handler._normalize_barcode("012345678905"), "012345678905")

    def test_float_rounds_correctly(self):
        self.assertEqual(data_handler._normalize_barcode(42.0), "42")

    def test_pandas_na(self):
        self.assertEqual(data_handler._normalize_barcode(pd.NA), "")


# ---------------------------------------------------------------------------
# load_file — CSV
# ---------------------------------------------------------------------------

class TestLoadFileCsv(unittest.TestCase):

    def _write_csv(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_basic_csv_load(self):
        path = self._write_csv("Column1,Goal,Correct approach\n111,Apple,A1\n222,Banana,B2\n")
        try:
            df = data_handler.load_file(path)
            self.assertEqual(len(df), 2)
            self.assertIn("Column1", df.columns)
        finally:
            os.unlink(path)

    def test_column1_normalized_from_scientific(self):
        # Simulate Excel-exported CSV where long barcodes become scientific notation strings
        path = self._write_csv("Column1,Goal\n1.94846E+11,Chips\n")
        try:
            df = data_handler.load_file(path)
            # _normalize_barcode now converts string scientific notation to a plain integer string
            self.assertEqual(df["Column1"].iloc[0], "194846000000")
        finally:
            os.unlink(path)

    def test_no_column1_still_loads(self):
        path = self._write_csv("Name,Value\nFoo,1\nBar,2\n")
        try:
            df = data_handler.load_file(path)
            self.assertEqual(len(df), 2)
            self.assertNotIn("Column1", df.columns)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# load_file — Excel
# ---------------------------------------------------------------------------

class TestLoadFileExcel(unittest.TestCase):

    def _make_excel(self, df: pd.DataFrame) -> str:
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        df.to_excel(path, index=False)
        return path

    def test_xlsx_load(self):
        df = _make_df()
        path = self._make_excel(df)
        try:
            loaded = data_handler.load_file(path)
            self.assertEqual(len(loaded), 3)
            self.assertIn("Column1", loaded.columns)
        finally:
            os.unlink(path)

    def test_xlsx_float_barcode_normalised(self):
        df = pd.DataFrame({"Column1": [194846000000.0], "Goal": ["Product"]})
        path = self._make_excel(df)
        try:
            loaded = data_handler.load_file(path)
            # _normalize_barcode now converts "194846000000.0" string to "194846000000"
            self.assertEqual(loaded["Column1"].iloc[0], "194846000000")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# find_by_barcode
# ---------------------------------------------------------------------------

class TestFindByBarcode(unittest.TestCase):

    def setUp(self):
        self.df = _make_df()

    def test_found_returns_index(self):
        idx = data_handler.find_by_barcode(self.df, "111")
        self.assertIsNotNone(idx)
        self.assertEqual(self.df.at[idx, "Goal"], "Apple")

    def test_not_found_returns_none(self):
        idx = data_handler.find_by_barcode(self.df, "999")
        self.assertIsNone(idx)

    def test_strips_whitespace(self):
        idx = data_handler.find_by_barcode(self.df, "  222  ")
        self.assertIsNotNone(idx)

    def test_no_column1_returns_none(self):
        df_no_col = pd.DataFrame({"Name": ["A", "B"]})
        idx = data_handler.find_by_barcode(df_no_col, "111")
        self.assertIsNone(idx)

    def test_returns_first_of_duplicates(self):
        df = pd.DataFrame({"Column1": ["dup", "dup"], "Goal": ["First", "Second"]})
        idx = data_handler.find_by_barcode(df, "dup")
        self.assertEqual(df.at[idx, "Goal"], "First")


# ---------------------------------------------------------------------------
# update_internal_id
# ---------------------------------------------------------------------------

class TestUpdateInternalId(unittest.TestCase):

    def test_updates_correct_approach(self):
        df = _make_df()
        result = data_handler.update_internal_id(df, "111", "NEW_ID")
        self.assertTrue(result)
        idx = data_handler.find_by_barcode(df, "111")
        self.assertEqual(df.at[idx, "Correct approach"], "NEW_ID")

    def test_not_found_returns_false(self):
        df = _make_df()
        result = data_handler.update_internal_id(df, "999", "X")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# update_goal
# ---------------------------------------------------------------------------

class TestUpdateGoal(unittest.TestCase):

    def test_updates_goal(self):
        df = _make_df()
        result = data_handler.update_goal(df, "222", "Mango")
        self.assertTrue(result)
        idx = data_handler.find_by_barcode(df, "222")
        self.assertEqual(df.at[idx, "Goal"], "Mango")

    def test_not_found_returns_false(self):
        df = _make_df()
        result = data_handler.update_goal(df, "999", "X")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# update_price
# ---------------------------------------------------------------------------

class TestUpdatePrice(unittest.TestCase):

    def test_updates_existing_price_column(self):
        df = _make_df()
        result = data_handler.update_price(df, "111", "5.99")
        self.assertTrue(result)
        idx = data_handler.find_by_barcode(df, "111")
        self.assertEqual(df.at[idx, "Price"], "5.99")

    def test_creates_price_column_if_missing(self):
        df = pd.DataFrame(
            [{"Column1": "444", "Goal": "Date", "Correct approach": "D004"}]
        )
        result = data_handler.update_price(df, "444", "2.49")
        self.assertTrue(result)
        self.assertIn("Price", df.columns)
        self.assertEqual(df.at[0, "Price"], "2.49")

    def test_not_found_returns_false(self):
        df = _make_df()
        result = data_handler.update_price(df, "999", "0.99")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# add_row
# ---------------------------------------------------------------------------

class TestAddRow(unittest.TestCase):

    def test_adds_new_row(self):
        df = _make_df()
        new_df = data_handler.add_row(df, "999", "Mango", "M009")
        self.assertEqual(len(new_df), 4)
        idx = data_handler.find_by_barcode(new_df, "999")
        self.assertIsNotNone(idx)
        self.assertEqual(new_df.at[idx, "Goal"], "Mango")
        self.assertEqual(new_df.at[idx, "Correct approach"], "M009")

    def test_duplicate_barcode_not_added(self):
        df = _make_df()
        new_df = data_handler.add_row(df, "111", "Duplicate", "DUP")
        self.assertEqual(len(new_df), 3)

    def test_returns_dataframe(self):
        df = _make_df()
        result = data_handler.add_row(df, "888", "X", "Y")
        self.assertIsInstance(result, pd.DataFrame)

    def test_original_df_unchanged_after_duplicate(self):
        df = _make_df()
        _ = data_handler.add_row(df, "111", "Dup", "D")
        self.assertEqual(len(df), 3)

    def test_add_row_to_empty_dataframe(self):
        df = pd.DataFrame()
        result = data_handler.add_row(df, "001", "Widget", "W001")
        self.assertEqual(len(result), 1)
        self.assertIn("Column1", result.columns)
        self.assertEqual(result["Column1"].iloc[0], "001")

    def test_add_row_fills_price_with_nan_when_column_exists(self):
        df = _make_df()  # has a Price column
        new_df = data_handler.add_row(df, "999", "Widget", "W999")
        idx = data_handler.find_by_barcode(new_df, "999")
        price_val = new_df.at[idx, "Price"]
        # pd.concat fills missing columns with NaN for new rows
        self.assertTrue(price_val is None or (isinstance(price_val, float) and math.isnan(price_val)))


# ---------------------------------------------------------------------------
# save_file — CSV
# ---------------------------------------------------------------------------

class TestSaveFileCsv(unittest.TestCase):

    def test_roundtrip_csv(self):
        df = _make_df()
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            data_handler.save_file(df, path)
            loaded = pd.read_csv(path, dtype=str)
            self.assertEqual(len(loaded), 3)
            self.assertIn("Column1", loaded.columns)
            self.assertEqual(loaded["Column1"].iloc[0], "111")
        finally:
            os.unlink(path)

    def test_csv_creates_new_file(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.unlink(path)  # delete so save_file must create it
        df = _make_df()
        try:
            data_handler.save_file(df, path)
            self.assertTrue(os.path.exists(path))
            loaded = pd.read_csv(path, dtype=str)
            self.assertEqual(len(loaded), 3)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_csv_overwrites_existing(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as f:
            f.write("old,data\n1,2\n")
        df = _make_df()
        try:
            data_handler.save_file(df, path)
            loaded = pd.read_csv(path, dtype=str)
            self.assertIn("Column1", loaded.columns)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# save_file — Excel
# ---------------------------------------------------------------------------

class TestSaveFileExcel(unittest.TestCase):

    def test_roundtrip_xlsx(self):
        df = _make_df()
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        try:
            data_handler.save_file(df, path)
            loaded = pd.read_excel(path, dtype=str)
            self.assertEqual(len(loaded), 3)
            self.assertIn("Column1", loaded.columns)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# generate_barcode_image
# ---------------------------------------------------------------------------

class TestGenerateBarcodeImage(unittest.TestCase):

    def test_returns_png_path(self):
        path = data_handler.generate_barcode_image("012345678905")
        try:
            self.assertTrue(os.path.exists(path), f"Expected file at {path}")
            self.assertTrue(path.endswith(".png"), f"Expected .png, got {path}")
        finally:
            if os.path.exists(path):
                os.unlink(path)
            # clean up temp dir
            parent = os.path.dirname(path)
            if os.path.isdir(parent):
                import shutil
                shutil.rmtree(parent, ignore_errors=True)

    def test_alphanumeric_barcode(self):
        path = data_handler.generate_barcode_image("ABC-123")
        try:
            self.assertTrue(os.path.exists(path))
        finally:
            parent = os.path.dirname(path)
            import shutil
            shutil.rmtree(parent, ignore_errors=True)

    def test_file_not_empty(self):
        path = data_handler.generate_barcode_image("TEST")
        try:
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            parent = os.path.dirname(path)
            import shutil
            shutil.rmtree(parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# save_file — FileLockError
# ---------------------------------------------------------------------------

class TestSaveFileFileLockError(unittest.TestCase):

    def test_csv_permission_error_raises_file_lock_error(self):
        df = _make_df()
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            with unittest.mock.patch("builtins.open", side_effect=PermissionError("locked")):
                with self.assertRaises(data_handler.FileLockError):
                    data_handler.save_file(df, path)
        finally:
            os.unlink(path)

    def test_xlsx_permission_error_raises_file_lock_error(self):
        df = _make_df()
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        try:
            with unittest.mock.patch("os.replace", side_effect=PermissionError("locked")):
                with self.assertRaises(data_handler.FileLockError):
                    data_handler.save_file(df, path)
        finally:
            if os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
