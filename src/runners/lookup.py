import asyncio
from typing import List, Optional, Tuple

import common
import lookup
from lookup.database.domains import DomainState
from runners.constants import LOOKUP_CONFIG_FILE, LOOKUP_LOG_FILE, prepare_start


class LookupRunner:
    def __init__(self, log_level=None):
        if log_level is not None:
            lookup.logger.setLevel(log_level)
        self.database: Optional[lookup.Database] = None
        self.crawler: Optional[lookup.Crawler] = None
        self.server: Optional[lookup.WebServer] = None
        self.fetcher: Optional[common.Fetcher] = None

    async def _prepare(self):
        if self.database:
            return
        prepare_start(LOOKUP_CONFIG_FILE, LOOKUP_LOG_FILE, lookup.Config, lookup.logger)

        self.database = lookup.Database()
        await self.database.setup()

    async def start(
        self, start_crawler: List[str] = None, start_server: bool = True
    ) -> None:
        """
        Start lookup server and/or crawler.
        :param start_crawler: None if don't start crawler. Else a list of starting urls.
        :param start_server: True if web server should be started else False.
        """
        await self._prepare()

        lookup.event_counter.all_time_fetched = (
            await self.database.queue.get_count_by_state(lookup.QueueState.Fetched)
        )
        lookup.event_counter.queue_size = await self.database.queue.get_size()
        lookup.event_counter.actor_count = await self.database.objects.get_object_cnt(
            lookup.AsObjectType.Actor
        )

        if start_crawler is not None:
            self.fetcher = common.Fetcher(
                lookup.logger, lookup.Config.parallel_fetches, lookup.Config.debug
            )
            await self.fetcher.setup()
            self.crawler = lookup.Crawler(self.database, self.fetcher)
            await self.crawler.run(start_crawler)

        if start_server:
            self.server = lookup.WebServer(self.database, self.crawler)
            await self.server.run()

    async def spin_and_log(self):
        while True:
            await asyncio.sleep(10)
            stats = lookup.event_counter.reset_stats()
            stats["queue_size"] = await self.database.queue.get_size()
            if self.crawler:
                stats["waiting_reachable"] = sum(
                    1
                    for d in self.crawler.domains.values()
                    if d.state <= DomainState.Unknown
                    and d.fail_streak == 0
                    and d.has_waiting_elements
                )
            await self.database.stats.insert(stats)

    async def add_verifier(self, verifier_uri) -> Tuple[int, str]:
        await self._prepare()
        fetcher = common.Fetcher(lookup.logger, debug=lookup.Config.debug)
        await fetcher.setup()
        verifier = await fetcher.fetch_ap(verifier_uri)
        key_pem = verifier["publicKey"]["publicKeyPem"]
        item = await self.database.verifiers.add(verifier["id"], key_pem)
        await fetcher.shutdown()
        return item["id"], item["uri"]

    async def cleanup(self):
        if self.crawler:
            await self.fetcher.shutdown()
        if self.server:
            await self.server.shutdown()
        if self.fetcher:
            await self.crawler.stop()
        if self.database:
            await self.database.close()
