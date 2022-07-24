from typing import Optional

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP


class Aliases:
    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS aliases"
            "(object_uri TEXT UNIQUE, object_id TEXT UNIQUE);"
        )

    async def insert(self, uri: str, oid: str):
        async with self.conn.execute(
            "REPLACE INTO aliases(object_uri, object_id) VALUES ($1, $2)",
            [uri, oid],
        ):
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()

    async def get_id(self, uri) -> Optional[str]:
        async with self.conn.execute(
            "SELECT object_id FROM aliases WHERE object_uri=$1", [uri]
        ) as cursor:
            packed_val = await cursor.fetchone()
            return None if packed_val is None else packed_val[0]
