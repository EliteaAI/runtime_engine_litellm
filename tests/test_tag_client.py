"""Unit tests for the LiteLLM tag client's quiet-check-before-update behaviour.

Run standalone (no pylon runtime needed):
    python3 tests/test_tag_client.py
"""

import os
import sys
import types
import unittest
from unittest.mock import Mock

import requests


def _load_api_module():
    """Load tools/api.py with the pylon.core.tools imports stubbed out."""
    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #
    pylon = types.ModuleType("pylon")
    pylon_core = types.ModuleType("pylon.core")
    pylon_tools = types.ModuleType("pylon.core.tools")
    #
    log_stub = types.ModuleType("pylon.core.tools.log")
    for name in ("info", "debug", "warning", "error", "exception"):
        setattr(log_stub, name, lambda *a, **kw: None)
    #
    web_stub = types.ModuleType("pylon.core.tools.web")
    web_stub.method = lambda *a, **kw: (lambda func: func)
    #
    pylon_tools.log = log_stub
    pylon_tools.web = web_stub
    #
    for name, mod in [
        ("pylon", pylon), ("pylon.core", pylon_core), ("pylon.core.tools", pylon_tools),
        ("pylon.core.tools.log", log_stub), ("pylon.core.tools.web", web_stub),
    ]:
        sys.modules.setdefault(name, mod)
    #
    sys.path.insert(0, os.path.join(plugin_root, "tools"))
    try:
        import api  # pylint: disable=C0415
        return api
    finally:
        sys.path.pop(0)


def _http_error(status_code, text=None):
    response = Mock()
    response.status_code = status_code
    response.text = text if text is not None else ("Tag not found" if status_code == 404 else "error")
    #
    error = requests.HTTPError(response=response)
    return error


class TestTagUpdateIfExists(unittest.TestCase):
    """tag_update_if_exists() is a no-op, returning None, for a tag /tag/update reports missing."""

    def setUp(self):
        api = _load_api_module()
        self.client = api.LiteLLMClient("http://litellm", "key")

    def test_missing_tag_returns_none(self):
        self.client.tag_update = Mock(side_effect=_http_error(404, "not found"))
        #
        result = self.client.tag_update_if_exists("missing_tag", max_budget=10.0)
        #
        self.assertIsNone(result)

    def test_existing_tag_is_updated(self):
        self.client.tag_update = Mock(return_value={"message": "ok"})
        #
        result = self.client.tag_update_if_exists("real_tag", max_budget=10.0)
        #
        self.assertEqual(result, {"message": "ok"})
        self.client.tag_update.assert_called_once_with(
            name="real_tag", max_budget=10.0, description=None,
        )

    def test_unrelated_error_from_tag_update_propagates(self):
        self.client.tag_update = Mock(side_effect=_http_error(500, "boom"))
        #
        with self.assertRaises(requests.HTTPError):
            self.client.tag_update_if_exists("real_tag", max_budget=10.0)


class TestTagUpsert(unittest.TestCase):
    """tag_upsert() tries /tag/update first, so a tag that already exists (the steady
    state) never touches /tag/new at all.
    """

    def setUp(self):
        api = _load_api_module()
        self.client = api.LiteLLMClient("http://litellm", "key")

    def test_existing_tag_is_updated_directly(self):
        self.client.tag_update = Mock(return_value={"message": "updated"})
        self.client.tag_new = Mock()
        #
        result = self.client.tag_upsert("real_tag", max_budget=10.0)
        #
        self.assertEqual(result, {"message": "updated"})
        self.client.tag_new.assert_not_called()

    def test_missing_tag_falls_back_to_create(self):
        self.client.tag_update = Mock(side_effect=_http_error(404, "not found"))
        self.client.tag_new = Mock(return_value={"message": "created"})
        #
        result = self.client.tag_upsert("new_tag", max_budget=10.0)
        #
        self.assertEqual(result, {"message": "created"})

    def test_race_with_another_worker_falls_back_to_update_again(self):
        self.client.tag_update = Mock(side_effect=[
            _http_error(404, "not found"), {"message": "updated"},
        ])
        self.client.tag_new = Mock(side_effect=_http_error(400, "already exists"))
        #
        result = self.client.tag_upsert("raced_tag", max_budget=10.0)
        #
        self.assertEqual(result, {"message": "updated"})
        self.assertEqual(self.client.tag_update.call_count, 2)

    def test_unrelated_error_from_tag_update_propagates(self):
        self.client.tag_update = Mock(side_effect=_http_error(500, "boom"))
        #
        with self.assertRaises(requests.HTTPError):
            self.client.tag_upsert("real_tag", max_budget=10.0)

    def test_unrelated_error_from_tag_new_propagates(self):
        self.client.tag_update = Mock(side_effect=_http_error(404, "not found"))
        self.client.tag_new = Mock(side_effect=_http_error(500, "boom"))
        #
        with self.assertRaises(requests.HTTPError):
            self.client.tag_upsert("new_tag", max_budget=10.0)


if __name__ == "__main__":
    unittest.main()
