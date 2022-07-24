import time
from enum import IntEnum
from random import randint
from typing import List

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP
from lookup.logging import event_counter

MAX_QUEUE_ID = 2**30


def rand_queue_id():
    return randint(0, MAX_QUEUE_ID)


class QueueState(IntEnum):
    """
    All Waiting > 0
    All processing = -waiting
    All others < min processing
    """

    Blocked = -6
    Redirected = -5
    Fetched = -4
    Failed = -3
    ProcessingPriority = -2
    Processing = -1
    Waiting = 1
    WaitingPriority = 2


class FifoQueue:
    def __init__(self):
        self.conn = None

    async def setup(self, connection: aiosqlite.Connection):
        self.conn = connection
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS queue ("
            "queue_id INTEGER,"  # for selecting random element
            "uri TEXT PRIMARY KEY,"  # uri of the resource
            "domain TEXT,"  # domain of the resource
            "found_in TEXT,"  # domain in which uri was found
            "state INTEGER,"  # state of the entry QueueState
            "next_update INTEGER,"  # when is the next update scheduled for
            "update_time INTEGER,"  # time between two updates
            "hash TEXT,"  # hash of the last crawled data
            "aux TEXT);"  # other data needed for the object handler
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS queue_domain_state_id_idx "
            "ON queue(domain, state DESC, queue_id);"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS queue_state_id_idx "
            "ON queue(state DESC, queue_id);"
        )
        await self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS queue_uri_idx ON queue(uri);"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS queue_next_update_idx "
            f"ON queue(next_update) WHERE state={QueueState.Fetched};"
        )

        await self.conn.execute(
            f"UPDATE queue SET state={QueueState.WaitingPriority} "
            f"WHERE state={QueueState.ProcessingPriority}"
        )
        await self.conn.execute(
            f"UPDATE queue SET state={QueueState.Waiting} "
            f"WHERE state={QueueState.Processing}"
        )

    async def get_size(self) -> int:
        async with self.conn.execute(
            f"SELECT count(*) FROM queue WHERE state = {QueueState.WaitingPriority}",
        ) as cursor:
            return (await cursor.fetchone())[0]

    async def insert(
        self,
        uri: str,
        domain: str,
        found_in: str,
        state: QueueState,
        update_time: int,
        aux: dict = None,
    ) -> bool:
        """
        Insert new uri to queue if it doesn't exist.
        Elements are compared based on URI. If URI already exists, no-op.
        :return: true if element is inserted else false.
        """
        async with self.conn.execute(
            "INSERT OR IGNORE INTO queue(uri, domain, found_in, state, "
            "queue_id, aux, next_update, update_time)"
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            [
                uri,
                domain,
                found_in,
                int(state),
                rand_queue_id(),
                aux,
                int(time.time() + update_time),
                int(update_time),
            ],
        ) as cursor:
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()
            return cursor.rowcount == 1

    async def set_next_to_update(self) -> None:
        await self.conn.execute(
            "UPDATE queue "
            f"SET state = {QueueState.WaitingPriority} "
            f"WHERE state = {QueueState.Fetched} "
            "AND next_update <= $1",
            [int(time.time())],
        )
        if COMMIT_AFTER_EVERY_OP:
            await self.conn.commit()

    async def get_last(self, count: int) -> List[dict]:
        async with self.conn.execute(
            "SELECT * FROM queue "
            f"WHERE (state = {QueueState.WaitingPriority} OR state = {QueueState.Waiting}) "
            "ORDER BY state DESC, queue_id DESC LIMIT $1",
            [count],
        ) as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
                if len(ret) >= count:
                    break
            return ret

    async def get_random(self, count: int) -> List[dict]:
        async with self.conn.execute(
            "SELECT * FROM queue "
            f"WHERE (state = {QueueState.WaitingPriority} OR state = {QueueState.Waiting}) "
            "AND queue_id > $1 "
            "ORDER BY state DESC, queue_id LIMIT $2",
            [rand_queue_id(), count],
        ) as cursor:
            ret = []
            event_counter.on_event(event_counter.SCHEDULE_RANDOM)
            async for row in cursor:
                ret.append(dict(row))
                if len(ret) >= count:
                    break
            if not ret:
                return await self.get_last(count)
            return ret

    async def get_last_from_domain(self, domain: str, count: int) -> List[dict]:
        async with self.conn.execute(
            "SELECT * FROM queue "
            f"WHERE (state = {QueueState.WaitingPriority}) "
            "AND domain = $1 "
            "ORDER BY state DESC, queue_id DESC LIMIT $2",
            [domain, count],
        ) as cursor:
            ret = []
            async for row in cursor:
                ret.append(dict(row))
                if len(ret) >= count:
                    break
            return ret

    async def get_random_from_domain(self, domain: str, count: int) -> List[dict]:
        async with self.conn.execute(
            "SELECT * FROM queue "
            f"WHERE (state = {QueueState.WaitingPriority}) "
            "AND domain = $1 AND queue_id > $2 "
            "ORDER BY state DESC, queue_id LIMIT $3",
            [domain, rand_queue_id(), count],
        ) as cursor:
            ret = []
            event_counter.on_event(event_counter.SCHEDULE_RANDOM_FROM_DOMAIN)
            async for row in cursor:
                ret.append(dict(row))
                if len(ret) >= count:
                    break
            if not ret:
                return await self.get_last_from_domain(domain, count)
            return ret

    async def get_waiting_domains(self) -> List[str]:
        async with self.conn.execute(
            "SELECT domain FROM queue "
            f"WHERE (state = {QueueState.WaitingPriority} OR state = {QueueState.Waiting}) "
            "GROUP BY domain",
        ) as cursor:
            ret = []
            async for row in cursor:
                ret.append(row["domain"])
            return ret

    async def get_domain_count_by_state(self, state: QueueState) -> List[str]:
        async with self.conn.execute(
            f"SELECT count(DISTINCT domain) FROM queue WHERE state = {state}",
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def get_element(self, uri: str) -> dict:
        async with self.conn.execute(
            "SELECT * FROM queue WHERE uri = $1", [uri]
        ) as cursor:
            row = await cursor.fetchone()
            return row and dict(row)

    async def get_count_by_state(self, state: QueueState) -> List[str]:
        async with self.conn.execute(
            f"SELECT count(*) FROM queue WHERE state = {state}",
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def update_state(self, uri: str, state: QueueState) -> None:
        async with self.conn.execute(
            "UPDATE queue SET state=$1, next_update=NULL WHERE uri=$2",
            [int(state), uri],
        ) as cursor:
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()
            return cursor.rowcount == 1

    async def update_state_time(
        self, uri: str, state: QueueState, update_time: int, ohash: str
    ) -> None:
        async with self.conn.execute(
            "UPDATE queue SET state=$1, next_update=$3, update_time=$2, hash=$4 WHERE uri=$5",
            [int(state), int(time.time() + update_time), int(update_time), ohash, uri],
        ) as cursor:
            if COMMIT_AFTER_EVERY_OP:
                await self.conn.commit()
            return cursor.rowcount == 1
