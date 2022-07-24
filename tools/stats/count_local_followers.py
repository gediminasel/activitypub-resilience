import asyncio
import json
import os.path

import src.lookup as lookup
from lookup.database.objects import AsObjectType

OUT_FILE = os.path.join("out", "follower_cnt.txt")

COLLECTION = "followers"


async def main():
    database = lookup.Database()
    await database.setup()

    counts = {}
    with open(OUT_FILE, "w") as f:
        async for actor in database.objects.get_object_stream(AsObjectType.Actor):
            data = json.loads(actor["json"])
            if COLLECTION not in data or data[COLLECTION] is None:
                continue

            followers_collection = data[COLLECTION]

            if isinstance(followers_collection, str):
                row = await database.objects.get_as_object(followers_collection)
                followers_collection = (
                    json.loads(row["json"]) if row is not None else None
                )

            if followers_collection is None or "totalItems" not in followers_collection:
                continue

            print(followers_collection["totalItems"], file=f)

    await database.close()

    sorted_counts = list(counts.items())
    sorted_counts.sort(key=lambda x: x[1], reverse=True)

    for domain, cnt in sorted_counts:
        print(domain, " " * (35 - len(domain)), cnt)


if __name__ == "__main__":
    asyncio.run(main())
