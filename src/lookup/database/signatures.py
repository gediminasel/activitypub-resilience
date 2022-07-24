from typing import List, Tuple

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP


class Signatures:
    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS signatures"
            "(verifier_id INTEGER, object_num INTEGER, signature TEXT, s_time INTEGER, "
            "PRIMARY KEY (verifier_id, object_num));"
        )

    async def insert(
        self, verifier_id: int, object_num: int, signature: str, s_time: int
    ) -> None:
        async with self.conn.execute(
            "REPLACE INTO signatures(verifier_id, object_num, signature, s_time) "
            "VALUES ($1, $2, $3, $4)",
            [verifier_id, object_num, signature, s_time],
        ):
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()

    async def get_not_signed(self, verifier_id: int, count: int) -> List[int]:
        async with self.conn.execute(
            "SELECT num FROM as_objects "
            "LEFT JOIN signatures ON "
            "   as_objects.num = signatures.object_num AND signatures.verifier_id=$1 "
            "WHERE signatures.object_num is NULL "
            "LIMIT $2",
            [verifier_id, count],
        ) as cursor:
            ret: List[int] = []
            async for row in cursor:
                ret.append(row["num"])
            return ret

    async def get_object_signatures(self, object_num: int) -> List[Tuple[int, str]]:
        async with self.conn.execute(
            "SELECT verifier_id, signature, s_time FROM signatures WHERE object_num = $1",
            [object_num],
        ) as cursor:
            ret: List[(int, str)] = []
            async for row in cursor:
                ret.append((row["verifier_id"], row["signature"], row["s_time"]))
            return ret
