import asyncio
from typing import Optional

import aiosqlite

from lookup.constants import COMMIT_AFTER_EVERY_OP
from lookup.database.aliases import Aliases
from lookup.database.domains import Domains
from lookup.database.objects import Objects
from lookup.database.queue import FifoQueue
from lookup.database.signatures import Signatures
from lookup.database.stats import Stats
from lookup.database.verifiers import Verifiers


class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

        self.domains: Domains = Domains()
        self.objects: Objects = Objects()
        self.aliases: Aliases = Aliases()
        self.queue: FifoQueue = FifoQueue()
        self.stats: Stats = Stats()
        self.signatures: Signatures = Signatures()
        self.verifiers: Verifiers = Verifiers()

        self._commit_task = (
            None
            if COMMIT_AFTER_EVERY_OP
            else asyncio.create_task(self._commit_periodically())
        )

    async def setup(self, path=None):
        self.conn = await aiosqlite.connect(path or "./out/database.db")
        self.conn.row_factory = aiosqlite.Row

        await self.domains.setup(self.conn)
        await self.objects.setup(self.conn)
        await self.aliases.setup(self.conn)
        await self.queue.setup(self.conn)
        await self.stats.setup(self.conn)
        await self.signatures.setup(self.conn)
        await self.verifiers.setup(self.conn)

    async def _commit_periodically(self):
        while True:
            await asyncio.sleep(3)
            await self.conn.commit()

    async def close(self):
        if self._commit_task is not None:
            self._commit_task.cancel()
        await self.conn.close()
