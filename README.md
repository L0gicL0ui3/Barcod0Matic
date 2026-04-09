# BarcodOmatic

BarcodOmatic is a desktop barcode and internal ID management app built with Python and PyQt6. It is designed for small retail, inventory, and back-room workflows where you need to scan a barcode, find the matching row in a spreadsheet, update the product name, internal SKU/ID, and price, then optionally generate and print a barcode label.

## What the App Does

- Scan or type a barcode to find a matching record in a CSV or Excel file
- Edit product name, internal ID, and price
- Look up unknown barcodes online using Open Food Facts, with UPCitemdb as fallback
- Add newly found online products into your data file
- Generate and print GS1-sized Code128 barcode labels
- Auto-load a default file from `UPCDirectory/UPCdata.csv`
- Use a desktop UI with a custom icon, dark theme, and resizable layout

## What You Need

To run the app reliably, you should have the following installed:

### Required software

- Windows 10 or Windows 11
- Python 3.10 or newer
- `pip` for installing Python packages

### Required Python packages

These are listed in `requirements.txt`:

- `PyQt6`
- `python-barcode[images]`
- `Pillow`
- `pandas`
- `openpyxl`

### Optional but recommended

- A USB barcode scanner that acts like a keyboard
- A printer configured in Windows if you want to print labels
- Internet access for online product lookup
- Git, if you want to clone or version the project

## Download Options

You can get the app in any of these ways:

### Option 1: Download from GitHub as ZIP

1. Open the GitHub repository page.
2. Click `Code`.
3. Click `Download ZIP`.
4. Extract the ZIP to a folder such as `C:\BarcodOmatic`.

### Option 2: Clone with Git

```bash
git clone https://github.com/YOUR_USERNAME/BarcodOmatic.git
cd BarcodOmatic
```

### Option 3: Use the local copied folder

If this project was shared directly, use the project folder as-is after extracting or copying it.

## Installation

Open Command Prompt or PowerShell in the project folder and run:

```bash
pip install -r requirements.txt
```

If `pip` does not work, try:

```bash
py -m pip install -r requirements.txt
```

## How to Run the App

From the project folder:

```bash
python main.py
```

If your system uses the Python launcher:

```bash
py main.py
```

## Files That Matter

- `main.py`: starts the application
- `app.py`: main PyQt6 window and UI logic
- `data_handler.py`: file loading, updates, saving, and barcode image generation
- `upc_lookup.py`: online product lookup logic
- `barcode_dialog.py`: barcode preview and print dialog
- `requirements.txt`: Python dependencies
- `icon.ico`: application icon
- `UPCDirectory/UPCdata.csv`: default auto-loaded data file

## Data File Requirements

The app expects a CSV or Excel file with these columns:

| Column | Required | Purpose |
|---|---|---|
| `Goal` | Yes | Product name or description |
| `Correct approach` | Yes | Internal SKU / internal ID |
| `Column1` | Yes | Barcode value |
| `Price` | No | Product price |

### Example

| Goal | Correct approach | Column1 | Price |
|---|---|---|---|
| Example Product | ITEM-0001 | 012345678905 | 4.99 |

### Notes

- `Column1` is the barcode column used for matching
- The app normalizes Excel barcode values so scientific notation does not break lookups
- Prices can be blank, but if entered they should be numeric

## Recommended Folder Structure

```text
BarcodOmatic/
	main.py
	app.py
	data_handler.py
	upc_lookup.py
	barcode_dialog.py
	requirements.txt
	icon.ico
	UPCDirectory/
		UPCdata.csv
```

If `UPCDirectory/UPCdata.csv` exists, BarcodOmatic loads it automatically on startup.

## Printing Requirements

For barcode printing to work well:

- Have a printer installed and working in Windows
- Use label media appropriate for barcode printing
- Keep printer scaling disabled or set to actual size when possible
- Use adequate print quality for scanner readability

The app generates GS1-style Code128 labels sized for reliable retail printing.

## Online Lookup Requirements

Online lookup depends on:

- Internet access
- Open Food Facts availability
- UPCitemdb availability for fallback requests

If both services return no result, the barcode will not be auto-added from online lookup.

## How to Use

1. Launch the app.
2. Load a CSV or Excel file, or use the default auto-loaded file.
3. Scan or type a barcode.
4. If found, edit the product name, price, and internal ID.
5. Click `Save Changes`.
6. Optionally click `Generate & Print Barcode...`.
7. If the barcode is not found, use `Look Up Online`.

## Troubleshooting

### App will not start

- Confirm Python is installed
- Confirm dependencies were installed from `requirements.txt`
- Run from a terminal to see any startup errors

### `ModuleNotFoundError`

One or more required packages are missing. Re-run:

```bash
pip install -r requirements.txt
```

### File locked during save

If the spreadsheet is open in Excel, VS Code, or another tool, Windows may lock the file. Close the file in other apps and save again, or use the app's Save As fallback.

### Barcode not found

- Check that the barcode is in the `Column1` column
- Confirm there are no extra spaces in the data file
- If importing from Excel, the app already normalizes scientific notation values

### Online lookup fails

- Check internet access
- The external service may not have that barcode
- UPCitemdb may be rate-limited on trial endpoints

## Best Results Checklist

For the smoothest experience, make sure all of these are true:

- Python 3.10+ is installed
- All dependencies from `requirements.txt` are installed
- Your data file includes `Goal`, `Correct approach`, and `Column1`
- Your barcode scanner is configured to send an Enter key after each scan
- Your printer is installed if you want labels
- Your default data file is placed in `UPCDirectory/UPCdata.csv` if you want auto-load on startup

## License

Add your preferred license before publishing publicly on GitHub if you want others to reuse or contribute to the project.
