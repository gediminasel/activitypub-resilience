import unittest
from unittest.mock import Mock

from aiohttp import web

import common.request as rq


def mock_request(query_params):
    request = Mock()
    request.query = query_params
    return request


class TestCommonRequest(unittest.TestCase):
    def test_get_str_query_param_given_invalid_key_raises_bad_request(self):
        request = mock_request({"valid": None})
        ex_text = "invalid key not found"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_str_query_param(request, "invalid_key", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_str_query_param_given_invalid_value_raises_bad_request(self):
        request = mock_request({"valid": None})
        ex_text = "invalid value"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_str_query_param(request, "valid", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_str_query_param_given_valid_value_returns_it(self):
        request = mock_request({"valid": "valid value"})
        result = rq.get_str_query_param(request, "valid", "text")
        self.assertEqual("valid value", result)

    def test_get_int_query_param_given_invalid_key_raises_bad_request(self):
        request = mock_request({"valid": None})
        ex_text = "invalid key not found"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_int_query_param(request, "invalid_key", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_int_query_param_given_none_value_raises_bad_request(self):
        request = mock_request({"valid": None})
        ex_text = "invalid value"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_int_query_param(request, "valid", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_int_query_param_given_string_value_raises_bad_request(self):
        request = mock_request({"valid": "asd"})
        ex_text = "invalid value"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_int_query_param(request, "valid", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_int_query_param_given_float_value_raises_bad_request(self):
        request = mock_request({"valid": "123.456"})
        ex_text = "invalid value"
        with self.assertRaises(web.HTTPBadRequest) as cm:
            rq.get_int_query_param(request, "valid", ex_text)
        self.assertEqual(ex_text, cm.exception.text)

    def test_get_int_query_param_given_valid_value_returns_it(self):
        request = mock_request({"valid": "123"})
        result = rq.get_int_query_param(request, "valid", "text")
        self.assertEqual(123, result)
