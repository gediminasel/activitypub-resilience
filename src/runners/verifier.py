import asyncio
import tracemalloc
from typing import List, Optional

import src.verifier as verifier
from common import signatures
from runners.constants import (
    VERIFIER_CONFIG_FILE,
    VERIFIER_KEY_FILE,
    VERIFIER_LOG_FILE,
    prepare_start,
)


class VerifierRunner:
    def __init__(self, log_level=None):
        if log_level is not None:
            verifier.logger.setLevel(log_level)
        self.server: Optional[verifier.WebServer] = None
        self.verifier: Optional[verifier.Verifier] = None
        self.signer: Optional[signatures.Signer] = None
        self.database: Optional[verifier.Database] = None

    async def start(self, lookups: List[str]) -> None:
        prepare_start(
            VERIFIER_CONFIG_FILE, VERIFIER_LOG_FILE, verifier.Config, verifier.logger
        )

        self.signer = signatures.Signer(4, VERIFIER_KEY_FILE)

        self.database = verifier.Database()
        await self.database.setup()

        self.server = verifier.WebServer(self.signer)
        await self.server.run()

        self.verifier = verifier.Verifier(self.signer, self.database)
        await self.verifier.run(lookups)

    async def spin_and_log(self):
        while True:
            await asyncio.sleep(10)
            stats = verifier.event_counter.reset_stats()
            if tracemalloc.is_tracing():
                _, peak_memory = tracemalloc.get_traced_memory()
                tracemalloc.reset_peak()
                stats["peak_memory"] = peak_memory
            if len(self.verifier.workers) > 0:
                worker = self.verifier.workers[0]
                stats["active_domains"] = sum(
                    1
                    for t_id, _ in worker.prev_domain_fetch.values()
                    if t_id in worker.tasks
                )
            await self.database.insert_stats(stats)

    async def run(self, lookups: List[str]):
        await self.start(lookups)
        await self.spin_and_log()

    async def cleanup(self):
        if self.verifier:
            await self.verifier.shutdown()
        if self.server:
            await self.server.shutdown()
        if self.signer:
            self.signer.shutdown()
        if self.database:
            await self.database.close()
