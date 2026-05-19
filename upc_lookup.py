import json
import os
import urllib.error
import urllib.request

_OFF_URL = "https://world.openfoodfacts.org/api/v0/product/{upc}.json"
_UPC_URL = "https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"
_BARCL_URL = "https://api.barcodelookup.com/v3/products?barcode={upc}&key={key}"


def _lookup_open_food_facts(upc: str) -> dict | None:
    """Query Open Food Facts (free, no rate limit) for a UPC/barcode.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found.
    """
    url = _OFF_URL.format(upc=upc)
    try:
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read().decode())
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None

    if data.get("status") != 1:
        return None

    product = data.get("product", {})
    title = product.get("product_name") or product.get("product_name_en") or ""
    brand = product.get("brands", "")
    # Clean up comma-separated brand list → take first entry
    if "," in brand:
        brand = brand.split(",")[0].strip()
    if not title:
        return None
    return {
        "title": title,
        "brand": brand,
        "model": "",
        "source": "Open Food Facts",
    }


def _lookup_upcitemdb(upc: str) -> dict | None:
    """Query UPCitemdb free API (100/day limit) for a UPC/barcode.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found.
    Raises urllib.error.HTTPError on 429 (rate limit) or 5xx errors.
    """
    url = _UPC_URL.format(upc=upc)
    try:
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    items = data.get("items", [])
    if not items:
        return None
    it = items[0]
    return {
        "title": it.get("title", ""),
        "brand": it.get("brand", ""),
        "model": it.get("model", ""),
        "source": "UPCitemdb",
    }


def _lookup_barcodelookup(upc: str) -> dict | None:
    """Query barcodelookup.com (requires BARCODELOOKUP_API_KEY env var) for a UPC/barcode.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found or if no API key is configured.
    Raises urllib.error.HTTPError on 429 (rate limit) or 5xx errors.

    Note: barcodelookup.com requires the API key as a URL query parameter; this
    is the authentication method defined by their API and cannot be changed.
    """
    api_key = os.environ.get("BARCODELOOKUP_API_KEY", "")
    if not api_key:
        return None
    url = _BARCL_URL.format(upc=upc, key=api_key)
    try:
        r = urllib.request.urlopen(url, timeout=10)
        data = json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    products = data.get("products", [])
    if not products:
        return None
    p = products[0]
    return {
        "title": p.get("title", ""),
        "brand": p.get("brand", ""),
        "model": p.get("model", ""),
        "source": "barcodelookup.com",
    }


def lookup_upc(upc: str) -> dict | None:
    """Look up a UPC/barcode using Open Food Facts, then UPCitemdb, then barcodelookup.com.

    Open Food Facts: free, unlimited, best for food/grocery products.
    UPCitemdb: 100 lookups/day free tier, covers broader retail categories.
    barcodelookup.com: broad retail catalog; requires BARCODELOOKUP_API_KEY env var.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found in any database.
    Raises urllib.error.HTTPError on rate-limit (429) or server errors from paid APIs.
    """
    result = _lookup_open_food_facts(upc)
    if result is not None:
        return result
    result = _lookup_upcitemdb(upc)
    if result is not None:
        return result
    return _lookup_barcodelookup(upc)
