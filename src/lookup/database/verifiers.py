from typing import Dict, Optional

import aiosqlite


class Verifiers:
    def __init__(self):
        self.conn = None
        self.by_uri: Dict[str, dict] = {}
        self.by_id: Dict[int, dict] = {}

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS verifiers"
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, uri TEXT UNIQUE, key_pem TEXT);"
        )

        async with self.conn.execute("SELECT * FROM verifiers") as cursor:
            async for row in cursor:
                d = dict(row)
                self.by_id[d["id"]] = d
                self.by_uri[d["uri"]] = d

    async def add(self, uri: str, key_pem: str) -> dict:
        await self.conn.execute(
            "INSERT INTO main.verifiers(uri, key_pem) VALUES ($1, $2)",
            [uri, key_pem],
        )
        await self.conn.commit()
        async with self.conn.execute(
            "SELECT * FROM verifiers WHERE uri=$1", [uri]
        ) as cursor:
            item = await cursor.fetchone()
            self.by_id[item["id"]] = item
            self.by_uri[item["uri"]] = item
            return item

    def get_by_id(self, vid: int) -> Optional[dict]:
        return self.by_id.get(vid, None)

    def get_by_uri(self, uri: str) -> Optional[dict]:
        return self.by_uri.get(uri, None)
