import unittest
from typing import Any, Tuple
from unittest.mock import AsyncMock, Mock, patch

from mocks.db import mock_lookup_db
from test_helpers import async_test

from common.webfinger import WebFinger
from lookup.database.objects import AsObjectType
from lookup.obj_handler import ObjectHandler


def testable_handler(
    mock_handle: bool = False,
) -> Tuple[ObjectHandler, Any, AsyncMock, Mock, list]:
    db = mock_lookup_db()
    webfinger = Mock(spec=WebFinger)
    on_id_found = AsyncMock()
    # noinspection PyTypeChecker
    handler = ObjectHandler(db, on_id_found, webfinger)

    handle_args = []
    if mock_handle:

        async def handle(
            obj, domain: str, priority: bool = False, top_level=False, aux=None
        ) -> None:
            handle_args.append((obj, domain, priority, top_level, aux))

        handler._handle = handle
    return handler, db, on_id_found, webfinger, handle_args


class TestObjectHandler(unittest.TestCase):
    @async_test
    async def test_handle_fields_given_string_fields_calls_handle(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": "a_val", "b": "b_val", "c": "c_val"}
        fields = ["a", "c"]
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        expected = ["a_val", "c_val"]
        self.assertListEqual(expected, [r[0] for r in handle_args])
        self.assertListEqual([domain] * len(expected), [r[1] for r in handle_args])
        self.assertListEqual([priority] * len(expected), [r[2] for r in handle_args])

    @async_test
    async def test_handle_fields_given_list_fields_calls_handle_for_every_element(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": ["a_val1", "a_val2", "a_val3"]}
        fields = ["a"]
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        expected = ["a_val1", "a_val2", "a_val3"]
        self.assertListEqual(expected, [r[0] for r in handle_args])
        self.assertListEqual([domain] * len(expected), [r[1] for r in handle_args])
        self.assertListEqual([priority] * len(expected), [r[2] for r in handle_args])

    @async_test
    async def test_handle_fields_given_list_and_str_fields_calls_handle_for_every_element(
        self,
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": ["a_val1", "a_val2", "a_val3"], "b": "b_val", "c": "c_val"}
        fields = ["a", "c"]
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        expected = ["a_val1", "a_val2", "a_val3", "c_val"]
        self.assertListEqual(expected, [r[0] for r in handle_args])
        self.assertListEqual([domain] * len(expected), [r[1] for r in handle_args])
        self.assertListEqual([priority] * len(expected), [r[2] for r in handle_args])

    @async_test
    async def test_handle_fields_given_empty_list_doesnt_call_handle(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": "a_val", "b": "b_val", "c": "c_val"}
        fields = []
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        self.assertListEqual([], handle_args)

    @async_test
    async def test_handle_fields_given_unknown_fields_doesnt_call_handle(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": "a_val", "b": "b_val", "c": "c_val"}
        fields = ["d", "e", "f"]
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        self.assertListEqual([], handle_args)

    @async_test
    async def test_handle_fields_ignores_unknown_fields_call_handle_for_valid(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": "a_val", "b": "b_val", "c": "c_val"}
        fields = ["a", "e", "f"]
        domain, priority = "example.com", False
        await handler._handle_fields(obj, fields, domain, priority)
        self.assertListEqual([("a_val", domain, priority, False, None)], handle_args)

    @async_test
    async def test_handle_fields_calls_handle_with_correct_domain(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": "a_val", "b": "b_val", "c": "c_val"}
        fields = ["a", "c", "e", "f"]
        domain, priority = "example.net", False
        await handler._handle_fields(obj, fields, domain, priority)
        expected = [
            ("a_val", domain, priority, False, None),
            ("c_val", domain, priority, False, None),
        ]
        self.assertListEqual(expected, handle_args)

    @async_test
    async def test_handle_fields_calls_handle_with_correct_priority(self):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"a": ["a_val1", "a_val2"], "b": "b_val", "c": "c_val"}
        fields = ["a", "c", "e", "f"]
        domain, priority = "example.com", True
        await handler._handle_fields(obj, fields, domain, priority)
        expected = [
            ("a_val1", domain, priority, False, None),
            ("a_val2", domain, priority, False, None),
            ("c_val", domain, priority, False, None),
        ]
        self.assertListEqual(expected, handle_args)

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_valid_actor_handles_fields(self, _patched_actor):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "actor_uri",
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        domain = "example.com"
        await handler._handle_actor(obj, domain)
        expected = [
            ("actor_outbox", domain, False, False, None),
            ("actor_followers", domain, True, False, None),
            ("actor_following", domain, True, False, None),
        ]
        self.assertSetEqual(set(expected), set(handle_args))

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_collection_given_valid_collection_handles_fields(
        self, _patched_actor
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "page_uri",
            "items": ["a", "b"],
            "orderedItems": ["c", "d"],
        }
        domain = "example.com"
        await handler._handle_collection_or_page(obj, domain, True)
        expected = [
            ("a", "example.com", True, False, {"colDir": "prev"}),
            ("b", "example.com", True, False, {"colDir": "prev"}),
            ("c", "example.com", True, False, {"colDir": "prev"}),
            ("d", "example.com", True, False, {"colDir": "prev"}),
        ]
        self.assertListEqual(expected, handle_args)

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_valid_actor_calls_db_insert(self, _patched_actor):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "actor_uri",
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        domain = "example.com"
        webfinger.resolve_actor_webfinger.return_value = None
        await handler._handle_actor(obj, domain)
        db.objects.insert.assert_awaited_once_with(
            "actor_uri", obj, AsObjectType.Actor, {"webfinger": None}
        )

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_valid_actor_calls_db_insert_with_correct_web_finger(
        self, _patched_actor
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "actor_uri",
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        domain = "example.com"
        webfinger.resolve_actor_webfinger.return_value = "actor_webfinger"
        await handler._handle_actor(obj, domain)
        db.objects.insert.assert_awaited_once_with(
            "actor_uri", obj, AsObjectType.Actor, {"webfinger": "actor_webfinger"}
        )

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_no_actor_id_doesnt_call_webfinger(
        self, _patched_actor
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        _patched_actor.return_value = None
        domain = "example.com"
        await handler._handle_actor(obj, domain)
        _patched_actor.assert_not_called()
        webfinger.resolve_actor_webfinger.assert_not_awaited()

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_not_trusted_domain_doesnt_call_webfinger(
        self, _patched_actor
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "actor_uri",
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        _patched_actor.return_value = None
        await handler._handle_actor(obj, None)
        _patched_actor.assert_not_called()
        webfinger.resolve_actor_webfinger.assert_not_awaited()

    @patch("lookup.obj_handler.actor_from_as")
    @async_test
    async def test_handle_actor_given_valid_actor_calls_webfinger_resolve(
        self, _patched_actor
    ):
        handler, db, ids_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {
            "uri": "actor_uri",
            "outbox": "actor_outbox",
            "followers": "actor_followers",
            "following": "actor_following",
        }
        _patched_actor.return_value = "acct:actor@example.com"
        domain = "example.com"
        await handler._handle_actor(obj, domain)
        _patched_actor.assert_called_once_with(obj, domain)
        webfinger.resolve_actor_webfinger.assert_awaited_once_with(
            "acct:actor@example.com", "actor_uri"
        )

    @async_test
    async def test__handle_given_string_calls_on_id_found(self):
        handler, db, id_found, *_ = testable_handler()
        obj = "object_id"
        domain, priority = "example.com", False
        await handler._handle(obj, domain, priority)
        id_found.assert_awaited_once_with(obj, domain, priority, None)

    @async_test
    async def test__handle_given_none_does_nothing(self):
        handler, db, id_found, *_ = testable_handler()
        obj = None
        domain, priority = "example.com", False
        await handler._handle(obj, domain, priority)
        id_found.assert_not_awaited()
        db.queue.update_state.assert_not_awaited()

    @async_test
    async def test__handle_given_person_without_id_calls_handle_actor(self):
        handler, db, id_found, *_ = testable_handler()
        handler._handle_actor = AsyncMock()
        obj = {"type": "Person"}
        domain, priority = "example.com", False
        await handler._handle(obj, domain, priority)
        id_found.assert_not_awaited()
        db.queue.update_state.assert_not_awaited()
        handler._handle_actor.assert_awaited_once_with(obj, domain)

    @async_test
    async def test__handle_given_person_with_trust_domain_id_calls_handle_actor(self):
        handler, db, id_found, *_ = testable_handler()
        handler._handle_actor = AsyncMock()
        oid = "https://example.com/actor/1"
        obj = {"uri": oid, "type": "Person"}
        domain, priority = "example.com", False
        db.queue.get_element.return_value = None
        await handler._handle(obj, domain, priority, top_level=True)
        id_found.assert_not_awaited()
        db.queue.insert.assert_awaited_once()
        handler._handle_actor.assert_awaited_once_with(obj, domain)

    @async_test
    async def test__handle_given_person_update_calls_update_state_time(self):
        handler, db, id_found, *_ = testable_handler()
        handler._handle_actor = AsyncMock()
        oid = "https://example.com/actor/1"
        obj = {"uri": oid, "type": "Person"}
        domain, priority = "example.com", False
        db.queue.get_element.return_value = {"hash": None}
        await handler._handle(obj, domain, priority, top_level=True)
        id_found.assert_not_awaited()
        db.queue.update_state_time.assert_awaited_once()

    @async_test
    async def test__handle_given_person_with_not_trust_id_calls_id_found(self):
        handler, db, id_found, *_ = testable_handler()
        handler._handle_actor = AsyncMock()
        oid = "https://example.com/actor/1"
        obj = {"uri": oid, "type": "Person"}
        domain, priority = "domain.net", False
        await handler._handle(obj, domain, priority)
        id_found.assert_awaited_once_with(oid, domain, priority, None)
        db.queue.update_state.assert_not_awaited()
        handler._handle_actor.assert_not_awaited()

    @async_test
    async def test_handle_given_string_calls__handle(self):
        handler, db, id_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = "object_id"
        domain, priority = "example.com", False
        await handler.handle(obj, domain, priority)
        self.assertListEqual([(obj, domain, priority, True, None)], handle_args)

    @async_test
    async def test_handle_given_obj_with_aux_calls__handle(self):
        handler, db, id_found, webfinger, handle_args = testable_handler(
            mock_handle=True
        )
        obj = {"type": "Person"}
        domain, priority, aux = "example.com", False, {"test": 1}
        await handler.handle(obj, domain, priority, aux)
        db.aliases.insert.assert_not_awaited()
        self.assertListEqual([(obj, domain, priority, True, aux)], handle_args)
