import json
import unittest
from unittest.mock import AsyncMock, Mock, call, patch

from mocks.db import mock_lookup_db
from test_helpers import async_test, raise_on_call

import lookup.signatures as sgn
from common.signatures import Verifier


@patch("lookup.signatures.logger.exception", Mock(side_effect=raise_on_call))
class TestLookupSignatures(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = Mock(spec=Verifier)
        self.verifier.verify = AsyncMock()

    signer = {"key_pem": "signer_key", "id": "signer_id"}

    @async_test
    async def test_add_signatures_given_empty_list_does_nothing(self):
        db = mock_lookup_db()
        await sgn.add_signatures(self.verifier, db, self.signer, [])
        self.assertEqual(0, db.subdbs_count)
        self.verifier.verify.assert_not_called()

    signature1: sgn.SignatureDict = {
        "uri": "object_id",
        "signature": "sign1",
        "signature_time": 100000,
    }
    signature2: sgn.SignatureDict = {
        "uri": "object_id2",
        "signature": "sign2",
        "signature_time": 200000,
    }
    actor_json = {"id": "id"}
    actor_aux = {"aux_key": "aux_val"}
    actor_repr = {
        "json": json.dumps(actor_json),
        "aux": json.dumps(actor_aux),
        "num": 1,
    }

    @async_test
    async def test_add_signatures_given_invalid_ids_does_nothing(self):
        db = mock_lookup_db()
        db.objects.get_as_object.return_value = None
        signatures = [self.signature1, self.signature2]
        await sgn.add_signatures(self.verifier, db, self.signer, signatures)
        self.assertEqual(1, db.subdbs_count)
        self.verifier.verify.assert_not_called()

    @async_test
    async def test_add_signatures_given_valid_id_calls_verify(self):
        db = mock_lookup_db()
        db.objects.get_as_object.return_value = self.actor_repr
        self.verifier.verify.return_value = False
        signatures = [self.signature1]
        await sgn.add_signatures(self.verifier, db, self.signer, signatures)
        self.verifier.verify.assert_awaited_once_with(
            self.actor_json, self.actor_aux, "signer_key", "sign1", 100000
        )
        db.signatures.insert.assert_not_called()

    @async_test
    async def test_add_signatures_given_valid_signature_calls_insert_signature(self):
        db = mock_lookup_db()
        db.objects.get_as_object.return_value = self.actor_repr
        self.verifier.verify.return_value = True
        signatures = [self.signature1]
        await sgn.add_signatures(self.verifier, db, self.signer, signatures)
        self.verifier.verify.assert_awaited_once_with(
            self.actor_json, self.actor_aux, "signer_key", "sign1", 100000
        )
        db.signatures.insert.assert_awaited_once_with("signer_id", 1, "sign1", 100000)

    @async_test
    async def test_add_signatures_given_invalid_ids_ignores_them(self):
        db = mock_lookup_db()

        async def get_as_obj(uri):
            if uri == "object_id":
                return self.actor_repr
            return None

        db.objects.get_as_object.side_effect = get_as_obj
        self.verifier.verify.return_value = True
        signatures = [self.signature1, self.signature2]
        await sgn.add_signatures(self.verifier, db, self.signer, signatures)
        self.verifier.verify.assert_awaited_once_with(
            self.actor_json, self.actor_aux, "signer_key", "sign1", 100000
        )
        db.signatures.insert.assert_awaited_once_with("signer_id", 1, "sign1", 100000)

    @async_test
    async def test_add_signatures_given_invalid_signatures_ignores_them(self):
        db = mock_lookup_db()
        db.objects.get_as_object.return_value = self.actor_repr

        async def verify(_json, _aux, _key, sign, _time):
            return sign == "sign1"

        self.verifier.verify.side_effect = verify
        signatures = [self.signature1, self.signature2]
        await sgn.add_signatures(self.verifier, db, self.signer, signatures)
        self.assertEqual(2, db.objects.get_as_object.call_count)
        self.verifier.verify.assert_has_awaits(
            [
                call(self.actor_json, self.actor_aux, "signer_key", "sign1", 100000),
                call(self.actor_json, self.actor_aux, "signer_key", "sign2", 200000),
            ],
            any_order=True,
        )
        db.signatures.insert.assert_awaited_once_with("signer_id", 1, "sign1", 100000)
