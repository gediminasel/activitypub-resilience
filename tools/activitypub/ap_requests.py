import base64
import json
import pprint
from email.utils import formatdate

import aiohttp
import requests
from Crypto.Hash import SHA256

from tools.activitypub.user import User


def http_date():
    return formatdate(timeval=None, localtime=False, usegmt=True)


def post_ap_activity(
    sender: User, receiver: User, message: dict, session: aiohttp.ClientSession
):
    body = json.dumps(message)
    body_digest = SHA256.new()
    body_digest.update(body.encode("utf-8"))
    body_digest = "sha-256=" + base64.b64encode(body_digest.digest()).decode("ascii")

    date = http_date()
    signed_string = (
        f"(request-target): post {receiver.inbox(True)}\n"
        f"host: {receiver.host()}\n"
        f"date: {date}\n"
        f"digest: {body_digest}"
    )

    signature = sender.sign(signed_string)

    headers = {
        "Host": receiver.host(),
        "Date": date,
        "Digest": body_digest,
        "Content-Type": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
        "Signature": f'keyId="{sender.main_key()}",'
        f'algorithm="rsa-sha256",'
        f'headers="(request-target) host date digest",'
        f'signature="{signature}"',
    }
    return session.post(receiver.inbox(), data=body, headers=headers)


def get_resource_pretty(url):
    r = requests.get(
        url,
        headers={
            "Accept": "application/activity+json, "
            'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
        },
    )
    print(r.status_code)
    return pprint.pformat(r.json())
