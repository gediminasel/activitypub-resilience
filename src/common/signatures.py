import asyncio
import base64
import binascii
import json
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Optional

# noinspection PyPackageRequirements
from Crypto.Hash import SHA256

# noinspection PyPackageRequirements
from Crypto.PublicKey import RSA

# noinspection PyPackageRequirements
from Crypto.PublicKey.RSA import RsaKey

# noinspection PyPackageRequirements
from Crypto.Signature import pkcs1_15


def _verify(data: str, signer_key: str, signature: str) -> bool:
    s_key = RSA.import_key(signer_key)
    h = SHA256.new(data.encode())
    try:
        pkcs1_15.new(s_key).verify(h, base64.b64decode(signature))
        return True
    except (ValueError, TypeError, binascii.Error):
        return False


key: Optional[RsaKey] = None
"""for multiprocessing"""


def _sign(data: str) -> str:
    global key
    h = SHA256.new(data.encode())
    return base64.b64encode(pkcs1_15.new(key).sign(h)).decode()


def _init_sign(key_pem: str) -> None:
    global key
    key = RSA.import_key(key_pem)


def get_data_to_sign(actor: dict, aux: dict, sign_time: int) -> Optional[str]:
    if not isinstance(actor, dict):
        return None
    actor_key = actor.get("publicKey", {})
    if not isinstance(actor_key, dict):
        return None
    to_sign = {
        "actor_id": actor.get("id", None),
        "actor_uri": actor.get("uri", None),
        "actor_type": actor.get("type", None),
        "actor_following": actor.get("following", None),
        "actor_followers": actor.get("followers", None),
        "actor_inbox": actor.get("inbox", None),
        "actor_outbox": actor.get("outbox", None),
        "actor_name": actor.get("name", None),
        "actor_url": actor.get("url", None),
        "actor_published": actor.get("published", None),
        "actor_endpoints": actor.get("endpoints", None),
        "webfinger": aux.get("webfinger", None),
        "key": actor_key,
        "signature_time": sign_time,
    }
    return json.dumps(to_sign, sort_keys=True, separators=(",", ":"))


class Verifier:
    def __init__(self, processes: int):
        self._executor = ProcessPoolExecutor(processes)

    async def verify(
        self, actor: dict, aux: dict, key_pem: str, signature: str, sign_time: int
    ) -> bool:
        loop = asyncio.get_event_loop()
        data = get_data_to_sign(actor, aux, sign_time)
        if data is None:
            return False
        return await loop.run_in_executor(
            self._executor, _verify, data, key_pem, signature
        )

    def shutdown(self):
        self._executor.shutdown()


class Signer:
    def __init__(
        self, processes: int, key_path: Optional[str], key_str: Optional[str] = None
    ):
        self.key: RsaKey = RSA.import_key(
            open(key_path).read() if key_path else key_str
        )
        self.key_pem = self.key.export_key()
        self._executor = ProcessPoolExecutor(
            processes, initializer=_init_sign, initargs=(self.key_pem,)
        )

    async def sign(self, actor: dict, aux: dict, sign_time: int) -> Optional[str]:
        data = get_data_to_sign(actor, aux, sign_time)
        if data is None:
            return None
        return await self._sign(data)

    async def _sign(self, data: str) -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, _sign, data)
        except BrokenProcessPool as e:
            raise asyncio.CancelledError() from e

    async def compare_and_sign(
        self, actor: dict, actor2: dict, aux: dict, sign_time: int
    ) -> Optional[str]:
        data = get_data_to_sign(actor, aux, sign_time)
        data2 = get_data_to_sign(actor2, aux, sign_time)
        if data is None or data != data2:
            return None
        return await self._sign(data)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
