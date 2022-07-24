from enum import IntEnum
from typing import List

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP


class DomainState(IntEnum):
    Blocked = 4
    AutoBlocked = 3
    Unreachable = 2
    Unknown = 1
    Safe = 0


class Domains:
    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS domains ("
            "domain TEXT PRIMARY KEY,"
            "next_req REAL,"  # next retry time
            "fail_streak INTEGER,"  # number of failed requests in a row
            "state INTEGER NOT NULL);"
        )

    async def get_all(self) -> List[dict]:
        async with self.conn.execute("SELECT * FROM domains") as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
            return ret

    async def count_by_state(self, state: DomainState) -> List[dict]:
        async with self.conn.execute(
            f"SELECT count(*) FROM domains WHERE state={state}"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def count_having_fail_streak(self) -> List[dict]:
        async with self.conn.execute(
            "SELECT count(*) FROM domains "
            f"WHERE fail_streak > 2 AND state = {DomainState.Unknown}"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def update_state(self, domain: str, state: DomainState) -> None:
        async with self.conn.execute(
            "UPDATE domains SET state = $1 WHERE domain = $2",
            [state, domain],
        ) as cursor:
            if cursor.rowcount == 0:
                await self.conn.execute(
                    "INSERT OR IGNORE INTO "
                    "domains(domain, fail_streak, next_req, state)"
                    "VALUES ($1, $2, $3, $4)",
                    [domain, 0, 0, state],
                )
        if COMMIT_AFTER_EVERY_OP:
            await self.conn.commit()

    async def update(self, domain: str, fail_streak: int, next_req: float) -> None:
        async with self.conn.execute(
            "REPLACE INTO domains(domain, fail_streak, next_req, state) "
            f"VALUES ($1, $2, $3, {DomainState.Unknown})",
            [domain, fail_streak, next_req],
        ):
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()
