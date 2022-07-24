import unittest
from unittest.mock import patch

from test_helpers import async_test

import common.logging as lg


class TestEventCounter(unittest.TestCase):
    def setUp(self) -> None:
        self.counter = lg.EventCounter()

    @async_test
    async def test_get_stats_returns_event_counts(self):
        self.counter.on_event("a")
        self.counter.on_event("b")
        self.counter.on_event("a")
        result = self.counter.get_stats()
        self.assertDictEqual(result | {"a": 2, "b": 1}, result)

    @async_test
    async def test_reset_stats_returns_event_counts(self):
        self.counter.on_event("a")
        self.counter.on_event("b")
        self.counter.on_event("a")
        result = self.counter.reset_stats()
        self.assertDictEqual(result | {"a": 2, "b": 1}, result)

    @async_test
    async def test_reset_stats_preserves_total_counts(self):
        self.counter.on_event("a")
        self.counter.on_event("b")
        result = self.counter.reset_stats()
        self.assertDictEqual(result | {"a": 1, "b": 1}, result)
        self.counter.on_event("a")
        result = self.counter.reset_stats()
        self.assertDictEqual(result | {"a": 1}, result)
        self.assertDictEqual({"a": 2, "b": 1}, self.counter.get_total_stats())

    @patch("common.logging.time.time")
    @async_test
    async def test_reset_stats_updates_last_flush(self, time_patch):
        time_patch.return_value = 3
        result = self.counter.reset_stats()
        self.assertDictEqual(result | {"time": 3}, result)

        self.counter.on_event("a")

        time_patch.return_value = 5
        result = self.counter.get_stats()
        self.assertDictEqual(result | {"a": 1, "time": 5, "period": 2}, result)

        self.counter.on_event("a")
        time_patch.return_value = 7
        result = self.counter.reset_stats()
        self.assertDictEqual(result | {"a": 2, "time": 7, "period": 4}, result)
