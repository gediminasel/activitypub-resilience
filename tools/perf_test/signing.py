import base64
import time

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

with open("res/verifier/key", "r") as key_file:
    key = RSA.importKey(key_file.read())


def sign() -> str:
    signature_digest = SHA256.new()
    signature_digest.update(data.encode("utf8"))
    signer = PKCS1_v1_5.new(key)
    return base64.b64encode(signer.sign(signature_digest)).decode("ascii")


if __name__ == "__main__":
    data = "0" * 1000

    a = time.time()
    for i in range(1000):
        sign()

    print(time.time() - a)
