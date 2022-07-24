import base64
from abc import abstractmethod
from typing import Optional

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


class User:
    def __init__(self) -> None:
        self.key = None

    @abstractmethod
    def uri(self, path_only: bool = False) -> str:
        raise NotImplementedError()

    @abstractmethod
    def main_key(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def host(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def inbox(self, path_only: bool = False) -> str:
        raise NotImplementedError()

    def followers(self) -> Optional[str]:
        return None

    def load_key(self, key_pem):
        self.key = RSA.importKey(key_pem)

    def load_key_f(self, filename):
        with open(filename, "r") as key_file:
            self.key = RSA.importKey(key_file.read())

    def sign(self, data: str) -> str:
        signature_digest = SHA256.new()
        signature_digest.update(data.encode("utf8"))
        signer = PKCS1_v1_5.new(self.key)
        return base64.b64encode(signer.sign(signature_digest)).decode("ascii")


class MastodonUser(User):
    def __init__(self, username, domain, protocol="https") -> None:
        super().__init__()
        self.username = username
        self.domain = domain
        self.protocol = protocol

    def uri(self, path_only: bool = False):
        if path_only:
            return f"/users/{self.username}"
        return f"{self.protocol}://{self.domain}/users/{self.username}"

    def host(self):
        return self.domain

    def inbox(self, path_only: bool = False):
        return f"{self.uri(path_only)}/inbox"

    def followers(self):
        return f"{self.uri()}/followers"

    def main_key(self):
        return f"{self.uri()}#main-key"


class RelayUser(User):
    def __init__(self, uri) -> None:
        super().__init__()
        self._uri = uri

    def uri(self, path_only: bool = False):
        if path_only:
            raise NotImplementedError()
        return self._uri

    def main_key(self):
        return f"{self.uri()}#main-key"

    def host(self) -> str:
        raise NotImplementedError()

    def inbox(self, path_only: bool = False) -> str:
        raise NotImplementedError()
