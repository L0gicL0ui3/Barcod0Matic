# BarcodOmatic

A desktop barcode and internal ID management app built with Python and PyQt6.

## Features

- Scan or type a barcode to look up a product record
- Edit product name, internal ID, and price
- Look up unknown barcodes online via Open Food Facts and UPCitemdb
- Generate and print GS1-standard Code128 barcodes (1.469" × 1.020" at 300 DPI)
- Auto-loads `UPCDirectory/UPCdata.csv` on startup
- Full dark theme (green / orange / purple)

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## Data File Format

The app works with CSV or Excel files containing these columns:

| Column | Description |
|---|---|
| `Goal` | Product name / description |
| `Correct approach` | Internal ID |
| `Column1` | Barcode (UPC/EAN/Code128) |
| `Price` | Price (optional) |

Place your data file at `UPCDirectory/UPCdata.csv` to have it auto-load on startup,
or use the **Browse** button to open any CSV or Excel file.
