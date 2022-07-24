import requests
from Crypto.Hash import SHA256
from pyld import jsonld

from tools.activitypub.user import User

ld_cache = {}


# noinspection PyUnusedLocal
def ld_context_loader(url, options):
    if url in ld_cache:
        return ld_cache[url]
    r = requests.get(url, headers={"Accept": "application/ld+json"})
    ld_cache[url] = {
        "contentType": r.headers["content-type"],
        "contextUrl": None,
        "documentUrl": url,
        "document": r.json(),
    }
    return ld_cache[url]


jsonld.set_document_loader(ld_context_loader)


def sha256_hash_jsonld(body: dict) -> str:
    norm = jsonld.normalize(
        body,
        {
            "algorithm": "URDNA2015",
            "format": "application/n-quads",
            "processingMode": "json-ld-1.0",
        },
    )
    body_digest = SHA256.new()
    body_digest.update(norm.encode("ascii"))
    return body_digest.hexdigest()


def attach_signature(creator: User, message: dict):
    signature = {
        "@context": "https://w3id.org/identity/v1",
        "creator": creator.main_key(),
        "published": "2021-10-28T23:50:11Z",
    }

    to_sign = sha256_hash_jsonld(signature) + sha256_hash_jsonld(message)

    del signature["@context"]
    signature["type"] = "RsaSignature2017"
    signature["signatureValue"] = creator.sign(to_sign)
    message["signature"] = signature
