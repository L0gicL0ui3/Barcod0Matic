"""Tests for upc_lookup.py — all HTTP calls are mocked."""
import io
import json
import sys
import os
import unittest
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import upc_lookup


def _make_response(payload: dict, status: int = 200) -> MagicMock:
    """Return a mock urllib response object for the given JSON payload."""
    body = json.dumps(payload).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="http://x", code=code, msg="err", hdrs=None, fp=None)


# ---------------------------------------------------------------------------
# _lookup_open_food_facts
# ---------------------------------------------------------------------------

class TestLookupOpenFoodFacts(unittest.TestCase):

    def _patch(self, payload, *, exc=None):
        if exc:
            return patch("urllib.request.urlopen", side_effect=exc)
        return patch("urllib.request.urlopen", return_value=_make_response(payload))

    def test_success_full(self):
        payload = {
            "status": 1,
            "product": {
                "product_name": "Test Chips",
                "brands": "BrandA",
            },
        }
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("012345678905")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Test Chips")
        self.assertEqual(result["brand"], "BrandA")
        self.assertEqual(result["model"], "")
        self.assertEqual(result["source"], "Open Food Facts")

    def test_fallback_to_product_name_en(self):
        payload = {
            "status": 1,
            "product": {
                "product_name": "",
                "product_name_en": "English Name",
                "brands": "B",
            },
        }
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertEqual(result["title"], "English Name")

    def test_brand_comma_split(self):
        payload = {
            "status": 1,
            "product": {
                "product_name": "Soda",
                "brands": "BrandX, BrandY",
            },
        }
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertEqual(result["brand"], "BrandX")

    def test_status_not_1_returns_none(self):
        payload = {"status": 0, "product": {}}
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertIsNone(result)

    def test_empty_title_returns_none(self):
        payload = {
            "status": 1,
            "product": {"product_name": "", "product_name_en": "", "brands": "B"},
        }
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertIsNone(result)

    def test_http_error_returns_none(self):
        with self._patch(None, exc=_make_http_error(500)):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertIsNone(result)

    def test_network_error_returns_none(self):
        with self._patch(None, exc=OSError("timeout")):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertIsNone(result)

    def test_missing_product_key(self):
        payload = {"status": 1}  # no "product" key
        with self._patch(payload):
            result = upc_lookup._lookup_open_food_facts("0")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# _lookup_go_upc
# ---------------------------------------------------------------------------

class TestLookupGoUpc(unittest.TestCase):

    def test_no_api_key_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            result = upc_lookup._lookup_go_upc("0")
        self.assertIsNone(result)

    def test_success(self):
        payload = {"product": {"name": "Widget", "brand": "Acme"}}
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "testkey"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_go_upc("012345678905")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Widget")
        self.assertEqual(result["brand"], "Acme")
        self.assertEqual(result["model"], "")
        self.assertEqual(result["source"], "Go-UPC")

    def test_404_returns_none(self):
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
                result = upc_lookup._lookup_go_upc("0")
        self.assertIsNone(result)

    def test_429_raises(self):
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    upc_lookup._lookup_go_upc("0")
        self.assertEqual(ctx.exception.code, 429)

    def test_empty_name_returns_none(self):
        payload = {"product": {"name": "", "brand": "B"}}
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_go_upc("0")
        self.assertIsNone(result)

    def test_no_product_key_returns_none(self):
        payload = {}  # no "product" key
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_go_upc("0")
        self.assertIsNone(result)

    def test_authorization_header_set(self):
        """Verify that the Authorization: Bearer header is sent with the API key."""
        payload = {"product": {"name": "Item", "brand": ""}}
        captured_req = []

        def fake_urlopen(req, timeout=None):
            captured_req.append(req)
            return _make_response(payload)

        with patch.dict(os.environ, {"GO_UPC_API_KEY": "secret123"}):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                upc_lookup._lookup_go_upc("111")

        self.assertTrue(len(captured_req) > 0)
        req = captured_req[0]
        self.assertIn("Authorization", req.headers)
        self.assertEqual(req.headers["Authorization"], "Bearer secret123")

    def test_network_error_returns_none(self):
        with patch.dict(os.environ, {"GO_UPC_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
                result = upc_lookup._lookup_go_upc("0")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# _lookup_upcitemdb
# ---------------------------------------------------------------------------

class TestLookupUpcitemdb(unittest.TestCase):

    def test_success(self):
        payload = {"items": [{"title": "Cool Hat", "brand": "HatCo", "model": "H1"}]}
        with patch("urllib.request.urlopen", return_value=_make_response(payload)):
            result = upc_lookup._lookup_upcitemdb("0")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Cool Hat")
        self.assertEqual(result["brand"], "HatCo")
        self.assertEqual(result["model"], "H1")
        self.assertEqual(result["source"], "UPCitemdb")

    def test_empty_items_returns_none(self):
        payload = {"items": []}
        with patch("urllib.request.urlopen", return_value=_make_response(payload)):
            result = upc_lookup._lookup_upcitemdb("0")
        self.assertIsNone(result)

    def test_missing_items_key_returns_none(self):
        payload = {}
        with patch("urllib.request.urlopen", return_value=_make_response(payload)):
            result = upc_lookup._lookup_upcitemdb("0")
        self.assertIsNone(result)

    def test_404_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
            result = upc_lookup._lookup_upcitemdb("0")
        self.assertIsNone(result)

    def test_429_raises(self):
        with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                upc_lookup._lookup_upcitemdb("0")
        self.assertEqual(ctx.exception.code, 429)

    def test_500_raises(self):
        with patch("urllib.request.urlopen", side_effect=_make_http_error(500)):
            with self.assertRaises(urllib.error.HTTPError):
                upc_lookup._lookup_upcitemdb("0")

    def test_first_item_used(self):
        payload = {
            "items": [
                {"title": "First", "brand": "B1", "model": "M1"},
                {"title": "Second", "brand": "B2", "model": "M2"},
            ]
        }
        with patch("urllib.request.urlopen", return_value=_make_response(payload)):
            result = upc_lookup._lookup_upcitemdb("0")
        self.assertEqual(result["title"], "First")


# ---------------------------------------------------------------------------
# _lookup_barcodelookup
# ---------------------------------------------------------------------------

class TestLookupBarcodelookup(unittest.TestCase):

    def test_no_api_key_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)

    def test_success(self):
        payload = {"products": [{"title": "Shoe", "brand": "Nike", "model": "Air"}]}
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Shoe")
        self.assertEqual(result["brand"], "Nike")
        self.assertEqual(result["model"], "Air")
        self.assertEqual(result["source"], "barcodelookup.com")

    def test_empty_products_returns_none(self):
        payload = {"products": []}
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)

    def test_404_returns_none(self):
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)

    def test_429_raises(self):
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    upc_lookup._lookup_barcodelookup("0")
        self.assertEqual(ctx.exception.code, 429)

    def test_missing_products_key_returns_none(self):
        payload = {}  # no "products" key
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)

    def test_500_raises(self):
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=_make_http_error(500)):
                with self.assertRaises(urllib.error.HTTPError):
                    upc_lookup._lookup_barcodelookup("0")

    def test_empty_title_returns_none(self):
        payload = {"products": [{"title": "", "brand": "B", "model": "M"}]}
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", return_value=_make_response(payload)):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)

    def test_network_error_returns_none(self):
        with patch.dict(os.environ, {"BARCODELOOKUP_API_KEY": "key"}):
            with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
                result = upc_lookup._lookup_barcodelookup("0")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# lookup_upc — chain logic
# ---------------------------------------------------------------------------

class TestLookupUpcChain(unittest.TestCase):

    _OFF_RESULT = {"title": "FROM_OFF", "brand": "B", "model": "", "source": "Open Food Facts"}
    _GOUPC_RESULT = {"title": "FROM_GOUPC", "brand": "B", "model": "", "source": "Go-UPC"}
    _UPC_RESULT = {"title": "FROM_UPC", "brand": "B", "model": "M", "source": "UPCitemdb"}
    _BARCL_RESULT = {"title": "FROM_BARCL", "brand": "B", "model": "M", "source": "barcodelookup.com"}

    def test_off_hit_returns_immediately(self):
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=self._OFF_RESULT) as m_off, \
             patch.object(upc_lookup, "_lookup_go_upc", return_value=self._GOUPC_RESULT) as m_goupc, \
             patch.object(upc_lookup, "_lookup_upcitemdb", return_value=self._UPC_RESULT) as m_upc, \
             patch.object(upc_lookup, "_lookup_barcodelookup", return_value=self._BARCL_RESULT) as m_barcl:
            result = upc_lookup.lookup_upc("0")
        self.assertEqual(result["source"], "Open Food Facts")
        m_goupc.assert_not_called()
        m_upc.assert_not_called()
        m_barcl.assert_not_called()

    def test_off_miss_go_upc_hit(self):
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=None), \
             patch.object(upc_lookup, "_lookup_go_upc", return_value=self._GOUPC_RESULT) as m_goupc, \
             patch.object(upc_lookup, "_lookup_upcitemdb", return_value=self._UPC_RESULT) as m_upc, \
             patch.object(upc_lookup, "_lookup_barcodelookup", return_value=self._BARCL_RESULT) as m_barcl:
            result = upc_lookup.lookup_upc("0")
        self.assertEqual(result["source"], "Go-UPC")
        m_upc.assert_not_called()
        m_barcl.assert_not_called()

    def test_off_and_goupc_miss_upcitemdb_hit(self):
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=None), \
             patch.object(upc_lookup, "_lookup_go_upc", return_value=None), \
             patch.object(upc_lookup, "_lookup_upcitemdb", return_value=self._UPC_RESULT) as m_upc, \
             patch.object(upc_lookup, "_lookup_barcodelookup", return_value=self._BARCL_RESULT) as m_barcl:
            result = upc_lookup.lookup_upc("0")
        self.assertEqual(result["source"], "UPCitemdb")
        m_barcl.assert_not_called()

    def test_off_goupc_upc_miss_barcl_hit(self):
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=None), \
             patch.object(upc_lookup, "_lookup_go_upc", return_value=None), \
             patch.object(upc_lookup, "_lookup_upcitemdb", return_value=None), \
             patch.object(upc_lookup, "_lookup_barcodelookup", return_value=self._BARCL_RESULT):
            result = upc_lookup.lookup_upc("0")
        self.assertEqual(result["source"], "barcodelookup.com")

    def test_all_miss_returns_none(self):
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=None), \
             patch.object(upc_lookup, "_lookup_go_upc", return_value=None), \
             patch.object(upc_lookup, "_lookup_upcitemdb", return_value=None), \
             patch.object(upc_lookup, "_lookup_barcodelookup", return_value=None):
            result = upc_lookup.lookup_upc("0")
        self.assertIsNone(result)

    def test_rate_limit_propagates(self):
        err = _make_http_error(429)
        with patch.object(upc_lookup, "_lookup_open_food_facts", return_value=None), \
             patch.object(upc_lookup, "_lookup_go_upc", side_effect=err):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                upc_lookup.lookup_upc("0")
        self.assertEqual(ctx.exception.code, 429)


if __name__ == "__main__":
    unittest.main()
