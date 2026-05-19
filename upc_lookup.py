import json
import urllib.error
import urllib.parse
import urllib.request

_OFF_URL = "https://world.openfoodfacts.org/api/v0/product/{upc}.json"
_UPC_URL = "https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"
_NUGET_REG_URL = "https://api.nuget.org/v3/registration5/{id}/index.json"
_NUGET_SEARCH_URL = "https://azuresearch-usnc.nuget.org/query?q={query}&take=1&prerelease=false"


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


def _lookup_nuget(upc: str) -> dict | None:
    """Look up a NuGet package by exact ID first, then by search query.

    Tries the NuGet v3 registration endpoint for an exact package ID match.
    Falls back to the NuGet search API if the exact ID is not found.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found.
    """
    # Try exact registration lookup first (package ID is case-insensitive in the URL)
    reg_url = _NUGET_REG_URL.format(id=urllib.parse.quote(upc.lower()))
    try:
        r = urllib.request.urlopen(reg_url, timeout=10)
        data = json.loads(r.read().decode())
        items = data.get("items", [])
        if items:
            # Each item group contains a list of version entries; grab the latest
            last_group = items[-1]
            leaf_items = last_group.get("items", [])
            entry = {}
            if leaf_items:
                entry = leaf_items[-1].get("catalogEntry", {})
            if not entry:
                # Sparse / external index — fall through to search
                pass
            else:
                pkg_id = entry.get("id", upc)
                authors = entry.get("authors", "")
                if isinstance(authors, list):
                    authors = ", ".join(authors)
                return {
                    "title": pkg_id,
                    "brand": authors,
                    "model": entry.get("version", ""),
                    "source": "NuGet",
                }
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    except Exception:
        pass

    # Fall back to NuGet search API
    search_url = _NUGET_SEARCH_URL.format(query=urllib.parse.quote(upc))
    try:
        r = urllib.request.urlopen(search_url, timeout=10)
        data = json.loads(r.read().decode())
    except Exception:
        return None

    hits = data.get("data", [])
    if not hits:
        return None
    pkg = hits[0]
    authors = pkg.get("authors", [])
    if isinstance(authors, list):
        authors = ", ".join(authors)
    return {
        "title": pkg.get("id", ""),
        "brand": authors,
        "model": pkg.get("version", ""),
        "source": "NuGet",
    }


def lookup_upc(upc: str) -> dict | None:
    """Look up a UPC/barcode using Open Food Facts, UPCitemdb, then NuGet as fallbacks.

    Open Food Facts: free, unlimited, best for food/grocery products.
    UPCitemdb: 100 lookups/day free tier, covers broader retail categories.
    NuGet: free, unlimited, covers .NET software packages.

    Returns a dict with keys: title, brand, model, source
    Returns None if not found in any database.
    Raises urllib.error.HTTPError on UPCitemdb 429 (rate limit) or 5xx errors.
    """
    result = _lookup_open_food_facts(upc)
    if result is not None:
        return result
    result = _lookup_upcitemdb(upc)
    if result is not None:
        return result
    return _lookup_nuget(upc)
