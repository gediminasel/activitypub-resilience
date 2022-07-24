import unittest

import common.activity_streams as streams


class TestActivityStreams(unittest.TestCase):
    object_with_uri = {"uri": "test"}
    object_with_id = {"id": "test"}
    object_with_uri_and_id = {"uri": "test_uri", "id": "test_id"}

    def test_get_uri_given_empty_dict_returns_none(self):
        result = streams.get_as_id({})
        self.assertIsNone(result)

    def test_get_uri_given_dict_with_id_returns_id(self):
        result = streams.get_as_id(self.object_with_id)
        self.assertEqual("test", result)

    def test_get_uri_given_dict_with_uri_returns_uri(self):
        result = streams.get_as_id(self.object_with_uri)
        self.assertEqual("test", result)

    def test_get_uri_given_dict_with_uri_and_id_returns_id(self):
        result = streams.get_as_id(self.object_with_uri_and_id)
        self.assertEqual("test_id", result)
