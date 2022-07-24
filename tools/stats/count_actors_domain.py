import asyncio
from urllib.parse import urlparse

import src.lookup as lookup
from lookup.database.objects import AsObjectType


async def main():
    database = lookup.Database()
    await database.setup()

    counts = {}
    async for actor in database.objects.get_object_stream(AsObjectType.Actor):
        domain = urlparse(actor["uri"]).netloc
        counts[domain] = counts.get(domain, 0) + 1

    await database.close()

    sorted_counts = list(counts.items())
    sorted_counts.sort(key=lambda x: x[1], reverse=True)

    for domain, cnt in sorted_counts:
        print(domain, " " * (35 - len(domain)), cnt)


if __name__ == "__main__":
    asyncio.run(main())
