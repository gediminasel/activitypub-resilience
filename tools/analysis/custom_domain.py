import asyncio
import json
from urllib.parse import urlparse

import src.lookup as lookup
from common.webfinger import split_actor
from lookup.database.objects import AsObjectType


def is_subdomain(subdomain, domain):
    if domain == subdomain:
        return True
    if "." not in subdomain or domain not in subdomain:
        return False
    return is_subdomain(subdomain.split(".", 1)[1], domain)


async def main():
    SHOW_SUBDOMAINS = False
    database = lookup.Database()
    await database.setup()
    try:
        count = 0
        with open("./out/custom_domains.txt", "w") as f:
            async for actor in database.objects.get_object_stream(AsObjectType.Actor):
                data = json.loads(actor["json"])
                aux = json.loads(actor["aux"])
                usr_domain = split_actor(aux.get("webfinger", None))
                actor_id = data["id"] if "id" in data else data.get("url", None)
                if actor_id is None or usr_domain is None:
                    continue
                uri_domain = urlparse(actor_id).netloc
                domain = usr_domain[1]
                if uri_domain != domain:
                    if not SHOW_SUBDOMAINS and (
                        is_subdomain(uri_domain, domain)
                        or is_subdomain(domain, uri_domain)
                    ):
                        continue
                    count += 1
                    print(actor_id, aux.get("webfinger", None), "uses custom domain")
                    print(
                        actor_id,
                        aux.get("webfinger", None),
                        "uses custom domain",
                        file=f,
                    )
            print("total:", count)
            print("total:", count, file=f)
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
