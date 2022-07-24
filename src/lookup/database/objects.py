import json
import time
from enum import IntEnum
from typing import AsyncIterable, List, Optional

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP


class AsObjectType(IntEnum):
    Actor = 2
    Feed = 1
    Other = 0


class Objects:
    PAGE_SIZE = 100

    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection) -> None:
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS as_objects"
            "(num INTEGER PRIMARY KEY AUTOINCREMENT, uri TEXT UNIQUE,"
            "type INTEGER, last_update REAL, json TEXT, aux TEXT);"
        )

    async def insert(
        self, uri: str, obj: dict, typ: AsObjectType, aux: Optional[dict] = None
    ) -> None:
        async with self.conn.execute(
            "REPLACE INTO as_objects(uri, type, json, last_update, aux)"
            "VALUES ($1, $2, $3, $4, $5)",
            [uri, typ, json.dumps(obj), time.time(), json.dumps(aux)],
        ):
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()

    async def get_as_object(self, uri: str) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM as_objects WHERE uri=$1", [uri]
        ) as cursor:
            item = await cursor.fetchone()
            if item is None:
                return None
            return dict(item)

    async def get_as_object_by_num(self, num: int) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM as_objects WHERE num=$1", [num]
        ) as cursor:
            item = await cursor.fetchone()
            if item is None:
                return None
            return dict(item)

    async def get_oldest_as_object(self, typ: AsObjectType) -> Optional[dict]:
        async with self.conn.execute(
            "SELECT * FROM as_objects WHERE type=$1 ORDER BY last_update", [typ]
        ) as cursor:
            item = await cursor.fetchone()
            if item is None:
                return None
            return dict(item)

    async def get_object_stream(self, typ: AsObjectType) -> AsyncIterable[dict]:
        async with self.conn.execute(
            "SELECT * FROM as_objects WHERE type=$1", [typ]
        ) as cursor:
            async for row in cursor:
                yield dict(row)

    async def get_object_cnt(self, typ: AsObjectType) -> int:
        async with self.conn.execute(
            "SELECT count(*) FROM as_objects WHERE type=$1", [typ]
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def get_objects_page(self, typ: AsObjectType, page: int) -> List[dict]:
        """
        Get objects of type `typ` with nums in page `page`.
        It might be empty because objects in this page might be of different type.
        :param typ: type to get
        :param page: page number to get
        :return: list of `typ` type objects in page `page`.
        """
        async with self.conn.execute(
            "SELECT * FROM as_objects WHERE type=$0 AND num > $1 AND num <= $2",
            [typ, page * Objects.PAGE_SIZE, (page + 1) * Objects.PAGE_SIZE],
        ) as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
            return ret

    async def get_page_count(self) -> List[dict]:
        async with self.conn.execute("SELECT max(num) FROM as_objects") as cursor:
            packed_val = await cursor.fetchone()
            if packed_val is None:
                val = 0
            else:
                val = packed_val[0]
            # round up
            return (val + Objects.PAGE_SIZE - 1) // Objects.PAGE_SIZE
