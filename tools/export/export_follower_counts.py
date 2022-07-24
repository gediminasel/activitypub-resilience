import asyncio
from os import path
from urllib.parse import urlparse

from tools.export.export_followers import ExportHandler, export_followers

GRAPH_FILE = path.join("out", "loc_ext_followers.txt")


class GraphTxtHandler(ExportHandler):
    def __init__(self):
        self.users = {}

    def actor_found(self, uri):
        self.users[uri] = [0, 0]

    async def new_actor(self, uri: str, data: dict, aux: str):
        self.actor_found(uri)

    async def follows(self, actor: str, follows: str):
        if urlparse(follows).netloc == urlparse(actor).netloc:
            self.users[actor][0] += 1
        else:
            self.users[actor][1] += 1


async def main():
    handler = GraphTxtHandler()
    await export_followers(handler)
    with open(GRAPH_FILE, "w") as f:
        for loc, ext in handler.users.values():
            if loc + ext > 0:
                print(loc, ext, file=f)


if __name__ == "__main__":
    asyncio.run(main())
