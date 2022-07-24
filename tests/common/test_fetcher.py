import unittest
from unittest.mock import Mock, patch

from mocks.web import mock_client_session
from test_helpers import async_test, raise_on_call

import common.fetcher as fetch


class TestFetcher(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = Mock(side_effect=raise_on_call)
        self.fetcher = fetch.Fetcher(self.logger, 1)

    @patch("common.fetcher.HIGHLY_RELIABLE_SITES", ["a", "b"])
    @async_test
    async def test_check_connection_returns_true_when_first_get_succeeds(self):
        self.fetcher.session = mock_client_session({"a": None})
        result = await self.fetcher.check_connection()
        self.assertTrue(result)
        # noinspection PyUnresolvedReferences
        self.assertEqual(1, self.fetcher.session.get.call_count)

    @patch("common.fetcher.HIGHLY_RELIABLE_SITES", ["a", "b"])
    @async_test
    async def test_check_connection_returns_true_when_second_get_succeeds(self):
        self.fetcher.session = mock_client_session({"b": None})
        result = await self.fetcher.check_connection()
        self.assertTrue(result)
        # noinspection PyUnresolvedReferences
        self.assertEqual(2, self.fetcher.session.get.call_count)

    @patch("common.fetcher.HIGHLY_RELIABLE_SITES", ["a", "b", "c"])
    @async_test
    async def test_check_connection_returns_false_when_all_get_fail(self):
        self.fetcher.session = mock_client_session({})
        result = await self.fetcher.check_connection()
        self.assertFalse(result)
        # noinspection PyUnresolvedReferences
        self.assertEqual(3, self.fetcher.session.get.call_count)

    @async_test
    async def test_setup_shutdown_not_fail(self):
        await self.fetcher.setup()
        await self.fetcher.shutdown()

    @async_test
    async def test_fetch_ap_given_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            await self.fetcher.fetch_ap(None)

    @async_test
    async def test_fetch_ap_given_no_scheme_raises_fetch_error(self):
        with self.assertRaises(fetch.FailedFetch):
            await self.fetcher.fetch_ap("no_scheme")

    @async_test
    async def test_fetch_ap_given_http_scheme_raises_fetch_error(self):
        self.fetcher.session = mock_client_session({})
        with self.assertRaises(fetch.FailedFetch):
            # noinspection HttpUrlsUsage
            await self.fetcher.fetch_ap("http://example.com/test")
        # noinspection PyUnresolvedReferences
        self.fetcher.session.assert_not_called()

    @async_test
    async def test_fetch_ap_given_local_url_raises_fetch_error(self):
        self.fetcher.session = mock_client_session({})
        with self.assertRaises(fetch.FailedFetch):
            await self.fetcher.fetch_ap("https://localhost/test")
        # noinspection PyUnresolvedReferences
        self.fetcher.session.assert_not_called()

    @async_test
    async def test_fetch_ap_given_local_url_with_port_raises_fetch_error(self):
        self.fetcher.session = mock_client_session({})
        with self.assertRaises(fetch.FailedFetch):
            await self.fetcher.fetch_ap("https://localhost:8000/test")
        # noinspection PyUnresolvedReferences
        self.fetcher.session.assert_not_called()

    @async_test
    async def test_fetch_ap_given_valid_url_calls_get(self):
        url = "https://example.com:8000/test"
        data = {"data": "data"}
        self.fetcher.session = mock_client_session({url: data})
        result = await self.fetcher.fetch_ap(url)
        # noinspection PyUnresolvedReferences
        self.fetcher.session.get.assert_called_once()
        self.assertDictEqual(data, result)

    @async_test
    async def test_fetch_ap_given_not_found_url_raises_fetch_error(self):
        url = "https://example.com:8000/test"
        self.fetcher.session = mock_client_session({url: None})
        with self.assertRaises(fetch.FailedFetch):
            await self.fetcher.fetch_ap(url)
        # noinspection PyUnresolvedReferences
        self.fetcher.session.get.assert_called_once()

    @async_test
    async def test_fetch_ap_given_server_error_500_raises_temporary_fetch(self):
        url = "https://example.com:8000/test"
        self.fetcher.session = mock_client_session({url: {"__http_status_code": 500}})
        with self.assertRaises(fetch.TemporaryFetchError):
            await self.fetcher.fetch_ap(url)
        # noinspection PyUnresolvedReferences
        self.fetcher.session.get.assert_called_once()

    @async_test
    async def test_fetch_ap_given_server_error_510_raises_temporary_fetch(self):
        url = "https://example.com:8000/test"
        self.fetcher.session = mock_client_session({url: {"__http_status_code": 510}})
        with self.assertRaises(fetch.TemporaryFetchError):
            await self.fetcher.fetch_ap(url)
        # noinspection PyUnresolvedReferences
        self.fetcher.session.get.assert_called_once()

    @async_test
    async def test_fetch_ap_given_no_internet_raises_temporary_fetch(self):
        url = "https://example.com:8000/test"
        self.fetcher.session = mock_client_session({})
        with self.assertRaises(fetch.TemporaryFetchError):
            await self.fetcher.fetch_ap(url)
        # noinspection PyUnresolvedReferences
        self.fetcher.session.get.assert_called_once()
