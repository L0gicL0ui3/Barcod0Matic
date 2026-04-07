import json
import urllib.error
import urllib.request

_OFF_URL = "https://world.openfoodfacts.org/api/v0/product/{upc}.json"
_UPC_URL = "https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"


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


def lookup_upc(upc: str) -> dict | None:
    """Look up a UPC/barcode using Open Food Facts first, then UPCitemdb as fallback.

    Open Food Facts: free, unlimited, best for food/grocery products.
    UPCitemdb: 100 lookups/day free tier, covers broader retail categories.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found in either database.
    Raises urllib.error.HTTPError on UPCitemdb 429 (rate limit) or 5xx errors.
    """
    result = _lookup_open_food_facts(upc)
    if result is not None:
        return result
    return _lookup_upcitemdb(upc)
