import asyncio
from os import path
from urllib.parse import urlparse

from tools.export.export_followers import ExportHandler, export_followers

ONLY_FIRST_N = 10_000_000_00
GRAPH_FILE = path.join("out", "graph.txt")


class StrToIntId:
    def __init__(self):
        self.map = {}

    def get(self, s: str):
        return self.get_is_new(s)[0]

    def get_is_new(self, s: str):
        if s in self.map:
            return self.map[s], False
        t = len(self.map)
        self.map[s] = t
        return t, True


class GraphTxtHandler(ExportHandler):
    def __init__(self):
        self.file = open(GRAPH_FILE, "w")
        self.domains = StrToIntId()
        self.users = StrToIntId()

    def actor_found(self, uri):
        actor_id, is_new = self.users.get_is_new(uri)

        if is_new:
            domain = urlparse(uri).netloc
            domain_id = self.domains.get(domain)
            print("A", actor_id, domain_id, file=self.file)

    async def new_actor(self, uri: str, data: dict, aux: str):
        self.actor_found(uri)

    async def follows(self, actor: str, follows: str):
        self.actor_found(follows)
        print("F", self.users.get(actor), self.users.get(follows), file=self.file)

    def close(self):
        self.file.close()


async def main():
    handler = GraphTxtHandler()
    await export_followers(handler, ONLY_FIRST_N)
    handler.close()


if __name__ == "__main__":
    asyncio.run(main())
