import unittest
from typing import Any, Tuple
from unittest.mock import AsyncMock

from mocks.db import mock_lookup_db
from test_helpers import async_test

from verifier.bounded_fetcher import BoundedFetcher


def testable_b_fetcher() -> Tuple[BoundedFetcher, Any, AsyncMock]:
    db = mock_lookup_db()
    b_fetcher = BoundedFetcher(10, db)
    b_fetcher.fetcher = AsyncMock()
    return b_fetcher, db, b_fetcher.fetcher


class TestBoundedFetcher(unittest.TestCase):
    @async_test
    async def test_fetch_ap_given_uri_calls_fetch_ap(self):
        uri = "https://example.com/"
        b_fetcher, db, fetcher = testable_b_fetcher()
        await b_fetcher.fetch_ap(uri)
        fetcher.fetch_ap.assert_awaited_once_with(uri)
