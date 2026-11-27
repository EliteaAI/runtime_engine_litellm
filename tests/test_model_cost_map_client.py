"""model_cost_map() reads the gateway's loaded catalog without runtime deployment registrations.

Run standalone (no pylon runtime needed):
    python3 tests/test_model_cost_map_client.py
"""

import unittest
from unittest.mock import Mock

from test_tag_client import _load_api_module


class TestModelCostMap(unittest.TestCase):

    def setUp(self):
        api = _load_api_module()
        self.client = api.LiteLLMClient("http://litellm", "key")
        self.client.session = Mock()
        self.client.session.get.return_value.json.return_value = {"gpt-5": {"mode": "chat"}}

    def test_the_catalog_is_requested_without_runtime_registrations(self):
        self.assertEqual(self.client.model_cost_map(timeout=8), {"gpt-5": {"mode": "chat"}})
        self.client.session.get.assert_called_once_with(
            "http://litellm/public/litellm_model_cost_map", params={"catalog_only": "true"}, timeout=8,
        )

    def test_the_client_default_timeout_applies_when_none_is_given(self):
        self.client.model_cost_map()
        self.assertEqual(self.client.session.get.call_args.kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
