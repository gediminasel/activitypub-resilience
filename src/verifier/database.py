import json
from typing import Dict, List, Optional

import aiosqlite

from verifier import Config


class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

    async def setup(self, path=None):
        self.conn = await aiosqlite.connect(path or "./out/verifier.db")
        self.conn.row_factory = aiosqlite.Row

        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS lookups(uri TEXT PRIMARY KEY, next_page INT DEFAULT 0);"
        )
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS domains(domain TEXT PRIMARY KEY, next_try REAL, fails INT);"
        )
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS queue"
            "(lookup TEXT, uri TEXT, next_fetch REAL, "
            "fails INT, json TEXT, aux TEXT, active INT DEFAULT 0, "
            "PRIMARY KEY(lookup, uri));"
        )
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS differences"
            "(lookup TEXT, uri TEXT, lookup_json TEXT, actual_json TEXT, time FLOAT, "
            "PRIMARY KEY(lookup, uri, time));"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS queue_next_fetch_idx "
            "ON queue(lookup, next_fetch) WHERE active = 0;"
        )
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS stats"
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, json TEXT);"
        )

    async def reset_queue(self) -> None:
        async with self.conn.execute("UPDATE queue SET active=0 WHERE active<>0"):
            pass

    async def add_to_queue(
        self,
        lookup: str,
        uri: str,
        next_fetch: float,
        fails,
        json_dump: Optional[str],
        aux: Optional[str],
        active: int = 0,
    ):
        async with self.conn.execute(
            "REPLACE INTO queue(lookup, uri, next_fetch, fails, json, aux, active) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            [lookup, uri, next_fetch, fails, json_dump, aux, active],
        ):
            if Config.commit_after_every:
                await self.conn.commit()

    async def remove_from_queue(self, lookup: str, uri: str):
        async with self.conn.execute(
            "DELETE FROM queue WHERE lookup=$1 AND uri=$2",
            [lookup, uri],
        ):
            if Config.commit_after_every:
                await self.conn.commit()

    async def get_from_queue(
        self, lookup: str, until_time: float, limit: int
    ) -> List[dict]:
        async with self.conn.execute(
            "SELECT * FROM queue WHERE lookup=$1 AND next_fetch < $2 AND active = 0 LIMIT $3",
            [lookup, until_time, limit],
        ) as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
            return ret

    async def set_active(self, lookup: str, uri: str) -> None:
        async with self.conn.execute(
            "UPDATE queue SET active=1 WHERE lookup=$1 AND uri=$2", [lookup, uri]
        ):
            if Config.commit_after_every:
                await self.conn.commit()

    async def get_next_page(self, lookup: str) -> int:
        async with self.conn.execute(
            "SELECT next_page FROM lookups WHERE uri=$1", [lookup]
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return 0
            return row[0]

    async def set_next_page(self, lookup: str, page_nr: int) -> None:
        async with self.conn.execute(
            "REPLACE INTO lookups(uri, next_page) VALUES ($1, $2)",
            [lookup, page_nr],
        ):
            await self.conn.commit()

    async def get_domains_dict(self) -> Dict[str, dict]:
        async with self.conn.execute("SELECT * FROM domains") as cursor:
            ret = {}
            async for row in cursor:
                ret[row["domain"]] = dict(row)
            return ret

    async def set_domain_state(self, domain: str, next_try: float, fails: int) -> None:
        async with self.conn.execute(
            "REPLACE INTO domains(domain, next_try, fails) VALUES ($1, $2, $3)",
            [domain, next_try, fails],
        ):
            if Config.commit_after_every:
                await self.conn.commit()

    async def insert_difference(
        self,
        lookup: str,
        uri: str,
        lookup_json: str,
        actual_json: str,
        timestamp: float,
    ) -> None:
        async with self.conn.execute(
            "INSERT INTO differences(lookup, uri, lookup_json, actual_json, time) "
            "VALUES ($1, $2, $3, $4, $5)",
            [lookup, uri, lookup_json, actual_json, timestamp],
        ):
            if Config.commit_after_every:
                await self.conn.commit()

    async def insert_stats(self, stats: dict) -> None:
        async with self.conn.execute(
            "INSERT INTO stats(json) VALUES ($1)",
            [json.dumps(stats)],
        ):
            await self.conn.commit()

    async def get_all_stats(self) -> List[dict]:
        async with self.conn.execute("SELECT * FROM stats ORDER BY id") as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
            return ret

    async def close(self):
        await self.conn.close()
