import json
import urllib.error
import unittest
from unittest.mock import patch

import upc_lookup


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class TestUpcLookup(unittest.TestCase):
    def test_lookup_open_food_facts_success(self):
        payload = {
            "status": 1,
            "product": {
                "product_name": "Sparkling Water",
                "brands": "Brand A, Brand B",
            },
        }
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = upc_lookup._lookup_open_food_facts("123")

        self.assertEqual(
            result,
            {
                "title": "Sparkling Water",
                "brand": "Brand A",
                "model": "",
                "source": "Open Food Facts",
            },
        )

    def test_lookup_open_food_facts_uses_product_name_en(self):
        payload = {"status": 1, "product": {"product_name_en": "English Name"}}
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = upc_lookup._lookup_open_food_facts("123")
        self.assertEqual(result["title"], "English Name")

    def test_lookup_open_food_facts_returns_none_on_missing_or_errors(self):
        with patch("urllib.request.urlopen", return_value=_FakeResponse({"status": 0})):
            self.assertIsNone(upc_lookup._lookup_open_food_facts("123"))

        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            self.assertIsNone(upc_lookup._lookup_open_food_facts("123"))

    def test_lookup_upcitemdb_success(self):
        payload = {"items": [{"title": "Item", "brand": "B", "model": "M"}]}
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = upc_lookup._lookup_upcitemdb("123")

        self.assertEqual(
            result,
            {"title": "Item", "brand": "B", "model": "M", "source": "UPCitemdb"},
        )

    def test_lookup_upcitemdb_returns_none_for_404_or_empty_items(self):
        err_404 = urllib.error.HTTPError(
            url="http://example.com",
            code=404,
            msg="not found",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err_404):
            self.assertIsNone(upc_lookup._lookup_upcitemdb("123"))

        with patch("urllib.request.urlopen", return_value=_FakeResponse({"items": []})):
            self.assertIsNone(upc_lookup._lookup_upcitemdb("123"))

    def test_lookup_upcitemdb_reraises_non_404_errors(self):
        err_429 = urllib.error.HTTPError(
            url="http://example.com",
            code=429,
            msg="rate limited",
            hdrs=None,
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err_429):
            with self.assertRaises(urllib.error.HTTPError):
                upc_lookup._lookup_upcitemdb("123")

    def test_lookup_upc_prefers_open_food_facts(self):
        off = {"title": "OFF", "brand": "", "model": "", "source": "Open Food Facts"}
        with (
            patch("upc_lookup._lookup_open_food_facts", return_value=off) as off_mock,
            patch("upc_lookup._lookup_upcitemdb") as upc_mock,
        ):
            result = upc_lookup.lookup_upc("123")

        self.assertEqual(result, off)
        off_mock.assert_called_once_with("123")
        upc_mock.assert_not_called()

    def test_lookup_upc_falls_back_to_upcitemdb(self):
        fallback = {"title": "UPC", "brand": "B", "model": "M", "source": "UPCitemdb"}
        with (
            patch("upc_lookup._lookup_open_food_facts", return_value=None) as off_mock,
            patch("upc_lookup._lookup_upcitemdb", return_value=fallback) as upc_mock,
        ):
            result = upc_lookup.lookup_upc("123")

        self.assertEqual(result, fallback)
        off_mock.assert_called_once_with("123")
        upc_mock.assert_called_once_with("123")


if __name__ == "__main__":
    unittest.main()
