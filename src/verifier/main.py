from typing import List

from common.signatures import Signer
from verifier import Config
from verifier.bounded_fetcher import BoundedFetcher
from verifier.database import Database
from verifier.worker import Worker


class Verifier:
    def __init__(self, signer: Signer, database: Database) -> None:
        self.signer: Signer = signer
        self.database: Database = database

        self.fetcher: BoundedFetcher = BoundedFetcher(
            Config.parallel_fetches, self.database
        )
        self.workers: List[Worker] = []

    async def run(self, lookups: List[str]) -> None:
        await self.database.reset_queue()
        await self.fetcher.setup()
        for lookup in lookups:
            worker = Worker(lookup, self.signer, self.database, self.fetcher)
            await worker.run()
            self.workers.append(worker)

    async def shutdown(self) -> None:
        for worker in self.workers:
            await worker.shutdown()
        await self.fetcher.shutdown()
