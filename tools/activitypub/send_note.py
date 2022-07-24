import asyncio
import json

import aiohttp

from tools.activitypub.activities import create_note_activity
from tools.activitypub.ap_requests import get_resource_pretty, post_ap_activity
from tools.activitypub.jsonld import attach_signature
from tools.activitypub.user import MastodonUser, RelayUser


async def send_note(content, reply_to=None):
    sender = MastodonUser("testt", "mastodon.lelesius.eu")
    sender.load_key_f("res/lelesius/testt.key")

    receiver = MastodonUser("gediminas", "localhost:3000", "http")

    message = create_note_activity(sender, content, reply_to)
    async with aiohttp.ClientSession() as session:
        async with post_ap_activity(sender, receiver, message, session) as r:
            print(r.status)
            print(await r.text())


async def send_note_relayed(content, reply_to=None):
    sender = MastodonUser("testt", "mastodon.lelesius.eu")
    sender.load_key_f("res/lelesius/testt.key")

    receiver = MastodonUser("gediminas", "localhost:3000", "http")

    message = create_note_activity(sender, content, reply_to)
    attach_signature(sender, message)

    relay = RelayUser("https://aprelay.lelesius.eu/actor")
    relay.load_key_f("res/lelesius/aprelay_actor.key")

    async with aiohttp.ClientSession() as session:
        async with post_ap_activity(relay, receiver, message, session) as r:
            print(r.status)
            print(await r.text())


if __name__ == "__main__":

    def print_msg():
        sender = RelayUser("https://aprelay.lelesius.eu/actor")
        sender.load_key_f("res/lelesius/aprelay_actor.key")
        message = create_note_activity(sender, "hello")
        attach_signature(sender, message)
        print(json.dumps(message))

    def fetch():
        print(get_resource_pretty("https://mastodon.lelesius.eu/users/admin"))

    def send():
        asyncio.run(
            send_note(
                """<p>Hello</p>""",
            )
        )

    def send_r():
        asyncio.run(
            send_note_relayed(
                """<p>reply to 6</p>""",
                "https://aprelay.lelesius.eu/actor/create_note/1640028943667",
            )
        )

    fetch()
