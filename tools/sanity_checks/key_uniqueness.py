import asyncio
import json
from urllib.parse import urlparse

import src.lookup as lookup
from lookup.database.objects import AsObjectType


async def main():
    database = lookup.Database()
    await database.setup()
    try:
        key_to_actor = {}

        domains_that_share_key = {"juick.com", "learnawesome.org", "gezondemedia.nl"}

        with open("./out/duplicate_keys.txt", "w") as f:
            async for actor in database.objects.get_object_stream(AsObjectType.Actor):
                data = json.loads(actor["json"])
                actor_id = data["id"] if "id" in data else data.get("url", None)
                if "publicKey" not in data:
                    continue
                public_key = data["publicKey"]
                key = public_key["publicKeyPem"]
                key_owner = public_key["owner"] if "owner" in public_key else actor_id
                owner = (actor_id, key_owner)

                if key in key_to_actor:
                    if key_to_actor[key][1] != owner[1]:
                        domain = urlparse(owner[1]).netloc
                        domain2 = urlparse(key_to_actor[key][1]).netloc
                        if domain != domain2 or domain not in domains_that_share_key:
                            print(key_to_actor[key], owner, "share the same key")
                            print(
                                key_to_actor[key], owner, "share the same key", file=f
                            )

                key_to_actor[key] = owner
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
