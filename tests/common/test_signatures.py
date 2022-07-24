import unittest
from unittest.mock import Mock

import pytest
from test_helpers import async_test

import common.signatures as sgn


# noinspection HttpUrlsUsage
class TestSignatures(unittest.TestCase):
    # noinspection SpellCheckingInspection
    private_key_rsa = """-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEA665o8jM9fdYD/bUcqe0vdXXmCH7KxLgbmNLr008pW43aqD7s
Kh8UOA+KpyrPU9QyHrrY4WNjVE0OXZeZYrEBVwAzJakv0npKXnFLc+cFoAwGKgfb
KLPVaarl+wt1IXVHNAo9nODlxHjzLKo3qF6ouPuUYuDJasVxsIFyOWUOYk12OvFf
79oU294LWkxf02C/iJY6CPmpmWdIaqlSdLmTrjx4TT4iBa9kSTZGAsgIEwFqVqbe
mf8vthSRfKOw3pJHATdjM3SxhlVJJk/3r8QMZ+WvGhjlGiz94AqWwShrgvrEteIl
Z1rIPP+p5Dn56vDM6m/4nTqaaM5Mle2Odnvw6wIDAQABAoIBAE5hSSavctZcLCSe
rIM4ze1HAfM2U7IbtpXbI7G5ZHw9z4ffsUQK5PsF9CtHOf9blTWSF1nR53FcVRg8
ODdRvavU9a2jODPMFtqU3C6WGNFS3mPxC+pb8HA9dVHJzDEN41nDxBzd0JxISztB
+tOkc4Fdrco6jtHTC03Tpwy+dourKvLhN449rfUWiLsNgYu2OWU9srM2aEo6jZl6
KHEvYBpNYqqAtMh3zvan6xYO87oTnGPbI/Sr6jap5DI+k99PcKS/qTUhEevlkwtX
BSykvxDnSjN8L+2xIMElC+S1YpoyFynmNIV2ancWt/1LaX30e9OXISz09XKtZrfF
xk95OvECgYEA9SH5NRLcgFxv7IunWhk8hkrkvD7rtzs3X9EiZEDmiW3pcV+XGwXC
NJOLiaA9+dfH23QCPeCacWhx2QILVIcdkA5TK31y17Kl87NWYPsupWpN3uQMtL1o
jpwMQZV59XDq40ev+wEE+jrfPoCaBz4ILfZRRtxbRP/gRRQW6FtKVPsCgYEA9iEr
9c2hZ5Lkgv1jnDthYyNDxuUD3nmpbJQCb5HX/kfM7bZDEEPQjrI+l4ESRWxevrOq
mkcxcLAS5GfXFh9I+Ys3QlZXpsf5gfE3HhgoSiRL2QjgJOZvqWujFMROQXSX18CT
KskOpStDZBPQor+hoKZjbpjlFY26+QFZIo8gsNECgYEAmpA4XVGuPTWL0P/hnrro
4dhZT6Tw5dDtwnnQkJwngKIQHs9iLMS9xn797eJfEakQOHx2aWO0nit4FZfnYv3r
EwklQffQsNbRMs9yeKYIrH5R6Wer507CnaEhTT0d8Deps3NhMAhdhhYW64cVF9ny
OGDmsKKC3gfk9kmLhCkDvn8CgYEAxYKDE2IrBsGC7HbIK4QfN34CEqaOv0YkJkRz
2/JOQPh/Q7bCBFhXEVuKDOv/rIQ1V5U370v4KbSxxGZr3I3IcrA77Nj6x5Sr7ZGT
KGw8UJrl3slXjWT58Bu3J6AMKEyW2QTpVCk5vmOEVdfs0d0zp4Y+Pm8lTnGIu+9Q
BwKSOjECgYEA1wmTbeh44r1LADYSNuMsjmpasWlrtXkhKOH7tuu+ImgieRW53o5I
+ZykFzGfF/vuBiW1yl6ceXEr6Hko5o210ynY59hcodSrG0TcHaTUwBBuV136VK7G
LX4m0nYM/5UNEEMUzRFRLB13tqOWyyyMqx9cYZ3t9a9x6pqz7ztXvFM=
-----END RSA PRIVATE KEY-----"""
    # noinspection SpellCheckingInspection
    public_key_pem = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA665o8jM9fdYD/bUcqe0v
dXXmCH7KxLgbmNLr008pW43aqD7sKh8UOA+KpyrPU9QyHrrY4WNjVE0OXZeZYrEB
VwAzJakv0npKXnFLc+cFoAwGKgfbKLPVaarl+wt1IXVHNAo9nODlxHjzLKo3qF6o
uPuUYuDJasVxsIFyOWUOYk12OvFf79oU294LWkxf02C/iJY6CPmpmWdIaqlSdLmT
rjx4TT4iBa9kSTZGAsgIEwFqVqbemf8vthSRfKOw3pJHATdjM3SxhlVJJk/3r8QM
Z+WvGhjlGiz94AqWwShrgvrEteIlZ1rIPP+p5Dn56vDM6m/4nTqaaM5Mle2Odnvw
6wIDAQAB
-----END PUBLIC KEY-----"""

    mastodon_actor = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
            {
                "Curve25519Key": "toot:Curve25519Key",
                "Device": "toot:Device",
                "Ed25519Key": "toot:Ed25519Key",
                "Ed25519Signature": "toot:Ed25519Signature",
                "EncryptedMessage": "toot:EncryptedMessage",
                "PropertyValue": "schema:PropertyValue",
                "alsoKnownAs": {"@id": "as:alsoKnownAs", "@type": "@id"},
                "cipherText": "toot:cipherText",
                "claim": {"@id": "toot:claim", "@type": "@id"},
                "deviceId": "toot:deviceId",
                "devices": {"@id": "toot:devices", "@type": "@id"},
                "discoverable": "toot:discoverable",
                "featured": {"@id": "toot:featured", "@type": "@id"},
                "featuredTags": {"@id": "toot:featuredTags", "@type": "@id"},
                "fingerprintKey": {"@id": "toot:fingerprintKey", "@type": "@id"},
                "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
                "identityKey": {"@id": "toot:identityKey", "@type": "@id"},
                "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
                "messageFranking": "toot:messageFranking",
                "messageType": "toot:messageType",
                "movedTo": {"@id": "as:movedTo", "@type": "@id"},
                "publicKeyBase64": "toot:publicKeyBase64",
                "schema": "http://schema.org#",
                "suspended": "toot:suspended",
                "toot": "http://joinmastodon.org/ns#",
                "value": "schema:value",
            },
        ],
        "attachment": [],
        "devices": "https://mastodon.example.com/users/admin/collections/devices",
        "discoverable": True,
        "endpoints": {"sharedInbox": "https://mastodon.example.com/inbox"},
        "featured": "https://mastodon.example.com/users/admin/collections/featured",
        "featuredTags": "https://mastodon.example.com/users/admin/collections/tags",
        "followers": "https://mastodon.example.com/users/admin/followers",
        "following": "https://mastodon.example.com/users/admin/following",
        "icon": {
            "mediaType": "image/jpeg",
            "type": "Image",
            "url": "https://mastodon.example.com/example.jpeg",
        },
        "id": "https://mastodon.example.com/users/admin",
        "inbox": "https://mastodon.example.com/users/admin/inbox",
        "manuallyApprovesFollowers": False,
        "name": "Test Test",
        "outbox": "https://mastodon.example.com/users/admin/outbox",
        "preferredUsername": "admin",
        "publicKey": {
            "id": "https://mastodon.example.com/users/admin#main-key",
            "owner": "https://mastodon.example.com/users/admin",
            "publicKeyPem": "-----BEGIN PUBLIC KEY-----\n"
            "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAn4tmuxgqTYt+o5R/ATwY\n"
            "hMvr1m/fO7E++DjwKL/XDCxBkezUBAwjMtICRaRh2mX5bvtMwMjpzBA/HNeCxySb\n"
            "kZYFTIVCSnm8I60oxQZHaLUE0BOkWHZKSzK8Qig8hMgTrMhdbD/woNyV2pjt7PTc\n"
            "23hB6LTaOxS/2B8lbnis6EmwYIA+N0y5lEFSfoqZ2e+oG4GtdhrzFeAdDIbas9/A\n"
            "iMUpr/mJ66URAXkG2ULXHCjUtxet8X1Aq4HXi8Smucz/xKgqqvqpo32LeQRtGRb6\n"
            "a7ohTaopjBxjUKG54jcDAwlyTG+tq4u5xxtgDCxGmBprdvVIw6U+lJOjV+Xyofw4\n"
            "hwIDAQAB\n"
            "-----END PUBLIC KEY-----\n",
        },
        "published": "2021-10-08T00:00:00Z",
        "summary": "<p></p>",
        "tag": [],
        "type": "Person",
        "url": "https://mastodon.example.com/@admin",
    }

    mastodon_actor_modified = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
            {
                "Curve25519Key": "toot:Curve25519Key",
                "Device": "toot:Device",
                "Ed25519Key": "toot:Ed25519Key",
                "Ed25519Signature": "toot:Ed25519Signature",
                "EncryptedMessage": "toot:EncryptedMessage",
                "PropertyValue": "schema:PropertyValue",
                "alsoKnownAs": {"@id": "as:alsoKnownAs", "@type": "@id"},
                "cipherText": "toot:cipherText",
                "claim": {"@id": "toot:claim", "@type": "@id"},
                "deviceId": "toot:deviceId",
                "devices": {"@id": "toot:devices", "@type": "@id"},
                "discoverable": "toot:discoverable",
                "featured": {"@id": "toot:featured", "@type": "@id"},
                "featuredTags": {"@id": "toot:featuredTags", "@type": "@id"},
                "fingerprintKey": {"@id": "toot:fingerprintKey", "@type": "@id"},
                "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
                "identityKey": {"@id": "toot:identityKey", "@type": "@id"},
                "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
                "messageFranking": "toot:messageFranking",
                "messageType": "toot:messageType",
                "movedTo": {"@id": "as:movedTo", "@type": "@id"},
                "publicKeyBase64": "toot:publicKeyBase64",
                "schema": "http://schema.org#",
                "suspended": "toot:suspended",
                "toot": "http://joinmastodon.org/ns#",
                "value": "schema:value",
            },
        ],
        "attachment": [],
        "devices": "https://mastodon.example.com/users/admin/collections/devices",
        "discoverable": True,
        "endpoints": {"sharedInbox": "https://mastodon.example.com/inbox"},
        "featured": "https://mastodon.example.com/users/admin/collections/featured",
        "featuredTags": "https://mastodon.example.com/users/admin/collections/tags",
        "followers": "https://mastodon.example.com/users/admin/followers",
        "following": "https://mastodon.example.com/users/admin/following",
        "icon": {
            "mediaType": "image/jpeg",
            "type": "Image",
            "url": "https://mastodon.example.com/example.jpeg",
        },
        "id": "https://mastodon.example.com/users/admin",
        "inbox": "https://mastodon.example.com/users/admin/inbox",
        "manuallyApprovesFollowers": False,
        "name": "Test Test",
        "outbox": "https://mastodon.example.com/users/admin/outbox",
        "preferredUsername": "admin",
        "publicKey": {
            "id": "https://mastodon.example.com/users/admin#main-key",
            "owner": "https://mastodon.example.com/users/admin",
            "publicKeyPem": "----------DIFFERENT_KEY----------",
        },
        "published": "2021-10-08T00:00:00Z",
        "summary": "<p></p>",
        "tag": [],
        "type": "Person",
        "url": "https://mastodon.example.com/@admin",
    }

    mastodon_actor_no_key = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
            {
                "Curve25519Key": "toot:Curve25519Key",
                "Device": "toot:Device",
                "Ed25519Key": "toot:Ed25519Key",
                "Ed25519Signature": "toot:Ed25519Signature",
                "EncryptedMessage": "toot:EncryptedMessage",
                "PropertyValue": "schema:PropertyValue",
                "alsoKnownAs": {"@id": "as:alsoKnownAs", "@type": "@id"},
                "cipherText": "toot:cipherText",
                "claim": {"@id": "toot:claim", "@type": "@id"},
                "deviceId": "toot:deviceId",
                "devices": {"@id": "toot:devices", "@type": "@id"},
                "discoverable": "toot:discoverable",
                "featured": {"@id": "toot:featured", "@type": "@id"},
                "featuredTags": {"@id": "toot:featuredTags", "@type": "@id"},
                "fingerprintKey": {"@id": "toot:fingerprintKey", "@type": "@id"},
                "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
                "identityKey": {"@id": "toot:identityKey", "@type": "@id"},
                "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
                "messageFranking": "toot:messageFranking",
                "messageType": "toot:messageType",
                "movedTo": {"@id": "as:movedTo", "@type": "@id"},
                "publicKeyBase64": "toot:publicKeyBase64",
                "schema": "http://schema.org#",
                "suspended": "toot:suspended",
                "toot": "http://joinmastodon.org/ns#",
                "value": "schema:value",
            },
        ],
        "attachment": [],
        "devices": "https://mastodon.example.com/users/admin/collections/devices",
        "discoverable": True,
        "endpoints": {"sharedInbox": "https://mastodon.example.com/inbox"},
        "featured": "https://mastodon.example.com/users/admin/collections/featured",
        "featuredTags": "https://mastodon.example.com/users/admin/collections/tags",
        "followers": "https://mastodon.example.com/users/admin/followers",
        "following": "https://mastodon.example.com/users/admin/following",
        "icon": {
            "mediaType": "image/jpeg",
            "type": "Image",
            "url": "https://mastodon.example.com/example.jpeg",
        },
        "id": "https://mastodon.example.com/users/admin",
        "inbox": "https://mastodon.example.com/users/admin/inbox",
        "manuallyApprovesFollowers": False,
        "name": "Test Test",
        "outbox": "https://mastodon.example.com/users/admin/outbox",
        "preferredUsername": "admin",
        "publicKey": "no-key",
        "published": "2021-10-08T00:00:00Z",
        "summary": "<p></p>",
        "tag": [],
        "type": "Person",
        "url": "https://mastodon.example.com/@admin",
    }

    actor_aux = {"webfinger": "admin@example.com", "other_data": "auxiliary_data"}

    actor_aux_modified = {"webfinger": "invalid", "other_data": "auxiliary_data"}

    def setUp(self):
        self.signer = sgn.Signer(1, None, self.private_key_rsa)
        self.verifier = sgn.Verifier(1)

    def tearDown(self):
        self.signer.shutdown()
        self.verifier.shutdown()

    @pytest.mark.integr
    @async_test
    async def test_verify_success_on_sign_return_value(self):
        time = 10000000
        signature = await self.signer.sign(self.mastodon_actor, self.actor_aux, time)
        is_valid = await self.verifier.verify(
            self.mastodon_actor, self.actor_aux, self.public_key_pem, signature, time
        )
        self.assertTrue(is_valid)

    @pytest.mark.integr
    @async_test
    async def test_verify_fails_if_sign_time_differs(self):
        time = 10000000
        signature = await self.signer.sign(self.mastodon_actor, self.actor_aux, time)
        is_valid = await self.verifier.verify(
            self.mastodon_actor,
            self.actor_aux,
            self.public_key_pem,
            signature,
            time + 1,
        )
        self.assertFalse(is_valid)

    @pytest.mark.integr
    @async_test
    async def test_verify_fails_if_public_key_differs(self):
        time = 10000000
        signature = await self.signer.sign(self.mastodon_actor, self.actor_aux, time)
        is_valid = await self.verifier.verify(
            self.mastodon_actor_modified,
            self.actor_aux,
            self.public_key_pem,
            signature,
            time,
        )
        self.assertFalse(is_valid)

    @pytest.mark.integr
    @async_test
    async def test_verify_fails_if_webfinger_differs(self):
        time = 10000000
        signature = await self.signer.sign(self.mastodon_actor, self.actor_aux, time)
        is_valid = await self.verifier.verify(
            self.mastodon_actor,
            self.actor_aux_modified,
            self.public_key_pem,
            signature,
            time,
        )
        self.assertFalse(is_valid)

    @pytest.mark.integr
    @async_test
    async def test_compare_and_sign_given_same_actor_returns_signature(self):
        time = 10000000
        signature = await self.signer.compare_and_sign(
            self.mastodon_actor, self.mastodon_actor, self.actor_aux, time
        )
        self.assertIsNotNone(signature)
        is_valid = await self.verifier.verify(
            self.mastodon_actor, self.actor_aux, self.public_key_pem, signature, time
        )
        self.assertTrue(is_valid)


class TestSignerUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.signer = Mock(spec=sgn.Signer)
        self.signer.sign = sgn.Signer.sign
        self.signer.compare_and_sign = sgn.Signer.compare_and_sign

    @async_test
    async def test_sign_given_actor_without_key_returns_none(self):
        time = 10000000
        signature = await self.signer.sign(
            self.signer,
            TestSignatures.mastodon_actor_no_key,
            TestSignatures.actor_aux,
            time,
        )
        self.assertIsNone(signature)
        self.signer._sign.assert_not_called()

    @async_test
    async def test_sign_given_actor_with_key_calls__sign(self):
        time = 10000000
        signature = await self.signer.sign(
            self.signer, TestSignatures.mastodon_actor, TestSignatures.actor_aux, time
        )
        self.assertIsNotNone(signature)
        self.signer._sign.assert_called_once()

    @async_test
    async def test_compare_and_sign_given_same_actor_returns_signature(self):
        time = 10000000
        signature = await self.signer.compare_and_sign(
            self.signer,
            TestSignatures.mastodon_actor,
            TestSignatures.mastodon_actor,
            TestSignatures.actor_aux,
            time,
        )
        self.assertIsNotNone(signature)
        self.signer._sign.assert_called_once()

    @async_test
    async def test_compare_and_sign_given_different_actors_returns_none(self):
        time = 10000000
        signature = await self.signer.compare_and_sign(
            self.signer,
            TestSignatures.mastodon_actor,
            TestSignatures.mastodon_actor_modified,
            TestSignatures.actor_aux,
            time,
        )
        self.assertIsNone(signature)
        self.signer._sign.assert_not_called()

    @async_test
    async def test_compare_and_sign_given_actor_without_key_returns_none(self):
        time = 10000000
        signature = await self.signer.compare_and_sign(
            self.signer,
            TestSignatures.mastodon_actor,
            TestSignatures.mastodon_actor_no_key,
            TestSignatures.actor_aux,
            time,
        )
        self.assertIsNone(signature)
        self.signer._sign.assert_not_called()
