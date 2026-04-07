import os
import re
import tempfile

import pandas as pd
from pathlib import Path


def _normalize_barcode(value) -> str:
    """Normalize barcode values that may be stored as scientific notation floats in Excel."""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return str(int(value))
    return str(value).strip()


def load_file(path: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame.

    Column1 (barcode column) is normalized from float/scientific notation
    to a plain integer string so lookups work correctly.
    """
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    # Normalize Column1 — Excel may store long barcodes as 1.94846E+11
    if "Column1" in df.columns:
        df["Column1"] = df["Column1"].apply(_normalize_barcode)

    return df


def find_by_barcode(df: pd.DataFrame, barcode: str):
    """Return the first row index whose Column1 matches the given barcode string.

    Returns None if no match is found.
    """
    barcode = barcode.strip()
    if "Column1" not in df.columns:
        return None

    matches = df[df["Column1"] == barcode]
    if matches.empty:
        return None

    return matches.index[0]


def update_internal_id(df: pd.DataFrame, barcode: str, new_id: str) -> bool:
    """Set the 'Correct approach' value for the row matching the given barcode.

    Returns True on success, False if the barcode was not found.
    """
    idx = find_by_barcode(df, barcode)
    if idx is None:
        return False

    df.at[idx, "Correct approach"] = new_id
    return True


def update_goal(df: pd.DataFrame, barcode: str, new_goal: str) -> bool:
    """Set the 'Goal' (product name) value for the row matching the given barcode.

    Returns True on success, False if the barcode was not found.
    """
    idx = find_by_barcode(df, barcode)
    if idx is None:
        return False

    df.at[idx, "Goal"] = new_goal
    return True


def update_price(df: pd.DataFrame, barcode: str, new_price: str) -> bool:
    """Set the 'Price' value for the row matching the given barcode.

    Returns True on success, False if the barcode was not found.
    Adds the Price column if it does not exist.
    """
    idx = find_by_barcode(df, barcode)
    if idx is None:
        return False

    if "Price" not in df.columns:
        df["Price"] = ""

    df.at[idx, "Price"] = new_price
    return True


class FileLockError(PermissionError):
    """Raised when the target file is locked by another process (e.g. VS Code, Excel)."""


def save_file(df: pd.DataFrame, path: str) -> None:
    """Overwrite the original file with the current DataFrame contents.

    Raises FileLockError if the file is locked by another process so the caller
    can offer the user a Save As fallback.
    """
    path = os.path.abspath(str(path))
    ext = Path(path).suffix.lower()
    import io as _io

    if ext in (".xlsx", ".xls"):
        dir_ = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=dir_)
        os.close(fd)
        try:
            df.to_excel(tmp_path, index=False)
            try:
                os.replace(tmp_path, path)
            except PermissionError as exc:
                raise FileLockError(
                    f"Cannot save — file is locked by another program.\n"
                    f"Close '{os.path.basename(path)}' in VS Code, Excel, or any "
                    f"other application, then try again.\n\nOr use Save As to save "
                    f"to a different location."
                ) from exc
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    else:
        buf = _io.StringIO()
        df.to_csv(buf, index=False)
        csv_bytes = buf.getvalue().encode("utf-8")
        try:
            with open(path, "r+b") as f:
                f.seek(0)
                f.write(csv_bytes)
                f.truncate()
        except PermissionError as exc:
            raise FileLockError(
                f"Cannot save — file is locked by another program.\n"
                f"Close '{os.path.basename(path)}' in VS Code, Excel, or any "
                f"other application, then try again.\n\nOr use Save As to save "
                f"to a different location."
            ) from exc


def add_row(df: pd.DataFrame, barcode: str, goal: str, internal_id: str) -> pd.DataFrame:
    """Append a new row to the DataFrame and return the updated DataFrame.

    Does nothing and returns the original DataFrame if the barcode already exists.
    """
    if find_by_barcode(df, barcode) is not None:
        return df
    new_row = pd.DataFrame(
        [{"Goal": goal, "Correct approach": internal_id, "Column1": barcode}]
    )
    return pd.concat([df, new_row], ignore_index=True)


def generate_barcode_image(barcode_value: str) -> str:
    """Generate a Code128 PNG barcode image for the given value.

    Saves to a temporary directory and returns the full path to the .png file.
    Code128 supports all ASCII characters, including alphanumeric and symbols.
    """
    import barcode as bc
    from barcode.writer import ImageWriter

    tmp_dir = tempfile.mkdtemp(prefix="barcode_")
    safe_name = re.sub(r"[^\w\-]", "_", barcode_value)[:60] or "barcode"
    base_path = os.path.join(tmp_dir, safe_name)
    code = bc.get("code128", barcode_value, writer=ImageWriter())
    # GS1 standard retail dimensions (Code 128 / UPC compatible)
    # X-dimension: 0.33mm, bar height: 22.85mm, 300 DPI for clean print quality
    options = {
        "module_width": 0.33,
        "module_height": 22.85,
        "quiet_zone": 6.5,
        "font_size": 10,
        "text_distance": 5.0,
        "dpi": 300,
    }
    return code.save(base_path, options=options)  # python-barcode appends .png
