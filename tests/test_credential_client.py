"""credential_exists() asks LiteLLM for one credential by name instead of listing every credential.

Run standalone (no pylon runtime needed):
    python3 tests/test_credential_client.py
"""

import unittest
from unittest.mock import Mock

import requests

from test_tag_client import _http_error, _load_api_module


class TestCredentialExists(unittest.TestCase):

    def setUp(self):
        api = _load_api_module()
        self.client = api.LiteLLMClient("http://litellm", "key")
        self.client._get_json = Mock(return_value={"credential_name": "7_cred"})

    def test_a_registered_credential_exists(self):
        self.assertTrue(self.client.credential_exists("7_cred", timeout=4))
        self.client._get_json.assert_called_once_with(endpoint="/credentials/by_name/7_cred", timeout=4)

    def test_a_missing_credential_does_not_exist(self):
        self.client._get_json.side_effect = _http_error(404, "Credential not found")
        self.assertFalse(self.client.credential_exists("7_cred"))

    def test_a_name_is_sent_as_one_path_segment(self):
        self.client.credential_exists("7_a/b c")
        self.assertEqual(self.client._get_json.call_args.kwargs["endpoint"], "/credentials/by_name/7_a%2Fb%20c")

    def test_other_gateway_errors_propagate(self):
        self.client._get_json.side_effect = _http_error(500, "boom")
        with self.assertRaises(requests.HTTPError):
            self.client.credential_exists("7_cred")


if __name__ == "__main__":
    unittest.main()
