import json
from typing import List, Optional

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP


class Stats:
    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS stats"
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, json TEXT);"
        )

    async def insert(self, stats: dict) -> None:
        async with self.conn.execute(
            "INSERT INTO stats(json) VALUES ($1)",
            [json.dumps(stats)],
        ):
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()

    async def get_last(self) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM stats ORDER BY id DESC LIMIT 1"
        ) as cursor:
            item = await cursor.fetchone()
            if item is None:
                return None
            return dict(item)

    async def get_all(self) -> List[dict]:
        async with self.conn.execute("SELECT * FROM stats ORDER BY id") as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
            return ret
