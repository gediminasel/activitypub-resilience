import unittest
from unittest.mock import AsyncMock

from mocks.web import mock_client_session
from test_helpers import async_test

import common.webfinger as wf


class TestWebfinger(unittest.TestCase):
    def test_split_actor_given_none_returns_none(self):
        actor = None
        # noinspection PyTypeChecker
        result = wf.split_actor(actor)
        self.assertIsNone(result)

    def test_split_actor_given_actor_returns_correct(self):
        actor = "acct:test@example.com"
        username, domain = wf.split_actor(actor)
        self.assertEqual("example.com", domain)
        self.assertEqual("test", username)

    def test_split_actor_given_invalid_actor_returns_none(self):
        actor = "no_actor_here"
        result = wf.split_actor(actor)
        self.assertIsNone(result)

    def test_get_meta_uri_given_invalid_actor_returns_none(self):
        actor = "no_actor_here"
        result = wf.get_meta_uri(actor)
        self.assertIsNone(result)

    def test_get_meta_uri_given_valid_actor_returns_url(self):
        actor = "acct:test@example.com"
        result = wf.get_meta_uri(actor)
        self.assertEqual("https://example.com/.well-known/host-meta", result)

    def test_get_webfinger_uri_given_invalid_actor_returns_none(self):
        actor = "no_actor_here"
        result = wf.get_webfinger_uri(actor)
        self.assertIsNone(result)

    def test_get_webfinger_uri_given_valid_actor_returns_url(self):
        actor = "acct:test@example.com"
        actor_webfinger = (
            "https://example.com/.well-known/webfinger?resource=acct:test@example.com"
        )
        result = wf.get_webfinger_uri(actor)
        self.assertEqual(actor_webfinger, result)

    # noinspection HttpUrlsUsage
    webfinger_response = {
        "subject": "acct:test@example.com",
        "aliases": ["https://example.com/@test", "https://example.com/users/test"],
        "links": [
            {
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": "correct_profile",
            },
            {"rel": "self", "type": "correct_type", "href": "correct_self"},
            {
                "rel": "http://ostatus.org/schema/1.0/subscribe",
                "template": "correct_template",
            },
        ],
    }

    webfinger_no_links_response = {"subject": "acct:test@example.com", "aliases": []}

    def test_find_link_given_existing_rel_returns_correct_entry(self):
        rel = "self"
        result = wf.find_link(self.webfinger_response, rel)
        self.assertEqual(rel, result["rel"])
        self.assertEqual("correct_self", result["href"])
        self.assertEqual("correct_type", result["type"])

    def test_find_link_given_non_existing_rel_returns_none(self):
        rel = "invalid_rel"
        result = wf.find_link(self.webfinger_response, rel)
        self.assertIsNone(result)

    def test_find_link_given_no_links_returns_none(self):
        rel = "self"
        result = wf.find_link(self.webfinger_no_links_response, rel)
        self.assertIsNone(result)

    mastodon_actor = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
        ],
        "id": "https://example.com/users/test",
        "inbox": "https://example.com/users/test/inbox",
        "outbox": "https://example.com/users/test/outbox",
        "preferredUsername": "test",
        "type": "Person",
        "url": "https://example.com/@test",
    }

    def test_actor_from_as_given_valid_as_actor_returns_correct_webfinger(self):
        result = wf.actor_from_as(self.mastodon_actor)
        self.assertEqual("acct:test@example.com", result)

    def test_actor_from_as_given_valid_as_actor_and_domain_returns_correct_webfinger(
        self,
    ):
        domain = "domain.net"
        result = wf.actor_from_as(self.mastodon_actor, domain)
        self.assertEqual("acct:test@domain.net", result)

    simple_actor = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
        ],
        "id": "https://example.net/users/simple_test",
        "type": "Person",
    }

    def test_actor_from_as_given_actor_without_username_returns_none(self):
        result = wf.actor_from_as(self.simple_actor)
        self.assertIsNone(result)

    host_meta_xml = """<?xml version="1.0" encoding="UTF-8"?>
<XRD xmlns="http://docs.oasis-open.org/ns/xri/xrd-1.0">
  <Link rel="lrdd" template="https://example.net/.well-known/webfinger?resource={uri}"/>
</XRD>
"""
    host_meta_lrdd_template = "https://example.net/.well-known/webfinger?resource="

    @async_test
    async def test_get_webfinger_meta_given_http_error_returns_none(self):
        url = "https://example.com/invalid"
        mock_session = mock_client_session({url: None})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.get_webfinger_meta(url)
        self.assertIsNone(result)

    @async_test
    async def test_get_webfinger_meta_given_invalid_xml_returns_none(self):
        response = "invalid<xml>"
        url = "https://example.com/invalid"
        mock_session = mock_client_session({url: response})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.get_webfinger_meta(url)
        self.assertIsNone(result)

    @async_test
    async def test_get_webfinger_meta_given_valid_xml_returns_parsed(self):
        url = "https://example.com/.well-known/host-meta"
        mock_session = mock_client_session({url: self.host_meta_xml})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.get_webfinger_meta(url)
        self.assertIsNotNone(result)

    @async_test
    async def test_resolve_webfinger_from_host_meta_given_valid_xml_calls_resolve(self):
        url = "https://example.com/.well-known/host-meta"
        actor = "acct:test@example.com"
        actor_uri = self.host_meta_lrdd_template + actor
        mock_session = mock_client_session({url: self.host_meta_xml})
        webfinger = wf.WebFinger(session=mock_session)
        webfinger.resolve_webfinger = AsyncMock()
        result = await webfinger.resolve_webfinger_from_host_meta(actor)
        self.assertIsNotNone(result)
        webfinger.resolve_webfinger.assert_awaited_once_with(actor, False, actor_uri)

    @async_test
    async def test_resolve_webfinger_from_host_meta_given_cached_xml_calls_resolve(
        self,
    ):
        url = "https://example.com/.well-known/host-meta"
        actor = "acct:test@example.com"
        actor_uri = self.host_meta_lrdd_template + actor
        mock_session = mock_client_session(None)
        webfinger = wf.WebFinger(session=mock_session)
        webfinger.meta_cache[url] = (1e12, self.host_meta_lrdd_template + "{uri}")
        webfinger.resolve_webfinger = AsyncMock()
        result = await webfinger.resolve_webfinger_from_host_meta(actor)
        self.assertIsNotNone(result)
        webfinger.resolve_webfinger.assert_awaited_once_with(actor, False, actor_uri)

    @async_test
    async def test_resolve_webfinger_from_host_meta_given_cached_none_returns_none(
        self,
    ):
        url = "https://example.com/.well-known/host-meta"
        actor = "acct:test@example.com"
        mock_session = mock_client_session(None)
        webfinger = wf.WebFinger(session=mock_session)
        webfinger.meta_cache[url] = (1e12, None)
        webfinger.resolve_webfinger = AsyncMock()
        result = await webfinger.resolve_webfinger_from_host_meta(actor)
        self.assertIsNone(result)
        webfinger.resolve_webfinger.assert_not_awaited()

    @async_test
    async def test_resolve_webfinger_from_host_meta_given_valid_xml_returns_actor(self):
        response = self.webfinger_response
        url = "https://example.com/.well-known/host-meta"
        actor = "acct:test@example.com"
        actor_uri = self.host_meta_lrdd_template + actor
        mock_session = mock_client_session(
            {url: self.host_meta_xml, actor_uri: response}
        )
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.resolve_webfinger_from_host_meta(actor)
        self.assertDictEqual(response, result)

    @async_test
    async def test_resolve_webfinger_given_invalid_actor_returns_none(self):
        mock_session = mock_client_session({})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.resolve_webfinger("invalid_actor")
        self.assertIsNone(result)

    @async_test
    async def test_resolve_webfinger_given_valid_url_returns_object(self):
        response = self.webfinger_response
        actor = "acct:test@example.com"
        url = "https://example.com/.well-known/webfinger?resource=acct:test@example.com"
        mock_session = mock_client_session({url: response})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.resolve_webfinger(actor)
        self.assertDictEqual(response, result)

    @async_test
    async def test_get_actor_webfinger_given_invalid_actor_returns_none(self):
        mock_session = mock_client_session({})
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.get_actor_webfinger("invalid_actor")
        self.assertIsNone(result)

    @async_test
    async def test_get_actor_webfinger_on_client_error_returns_none(self):
        mock_session = mock_client_session(None)
        webfinger = wf.WebFinger(session=mock_session)
        result = await webfinger.get_actor_webfinger("invalid_actor")
        self.assertIsNone(result)

    @async_test
    async def test_get_actor_webfinger_given_different_domain(self):
        actor = "acct:test@test.example.com"
        diff_actor = "acct:test@example.com"
        response = {"subject": diff_actor, "links": [{"rel": "self", "href": "result"}]}
        mock_session = mock_client_session(None)
        webfinger = wf.WebFinger(session=mock_session)
        webfinger.resolve_webfinger = AsyncMock()
        webfinger.resolve_webfinger.return_value = response
        result = await webfinger.get_actor_webfinger(actor)
        self.assertEqual((diff_actor, "result"), result)
