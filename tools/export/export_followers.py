import json
import random
from abc import abstractmethod

import lookup
from common.activity_streams import get_as_id
from lookup.database.objects import AsObjectType


class ExportHandler:
    @abstractmethod
    async def new_actor(self, uri: str, data: dict, aux: str):
        pass

    @abstractmethod
    async def follows(self, actor: str, follows: str):
        pass


async def export_followers(
    handler: ExportHandler, first_n: int = 1000_000_000, every_nth=None
):
    lookup_db = lookup.Database()
    await lookup_db.setup(r"C:\Users\gedim\Desktop\database.db")

    count = 0
    async for actor in lookup_db.objects.get_object_stream(AsObjectType.Actor):
        count += 1
        if count > first_n:
            break
        if count % 1000 == 0:
            print("exported", count)

        actor_uri = actor["uri"]

        if every_nth is not None and random.randint(1, every_nth) != 1:
            continue

        actor_data = json.loads(actor["json"])
        await handler.new_actor(actor_uri, actor_data, actor["aux"])

        if "following" not in actor_data:
            continue

        following_col = await lookup_db.objects.get_as_object(actor_data["following"])
        if following_col is None:
            continue
        following_col = json.loads(following_col["json"])
        if following_col is None or "first" not in following_col:
            continue

        following_page = following_col["first"]
        for i in range(10000):
            if following_page is None:
                break

            if isinstance(following_page, str):
                page = await lookup_db.objects.get_as_object(following_page)
                if page is None:
                    break
                page = json.loads(page["json"])
            elif not isinstance(following_page, dict):
                print("UNKNOWN PAGE", following_page)
                break
            else:
                page = following_page

            if page is None or ("orderedItems" not in page and "items" not in page):
                break
            items = page["orderedItems"] if "orderedItems" in page else page["items"]
            for follower in items:
                if follower is None:
                    continue
                uri = follower if isinstance(follower, str) else get_as_id(follower)
                await handler.follows(actor_uri, uri)

            if "next" not in page:
                break
            following_page = page["next"]

    await lookup_db.close()
