import asyncio
import time
from typing import Dict
from urllib.parse import urlparse

from common.constants import INF_TIME_CONST
from common.fetcher import FailedFetch, Fetcher, TemporaryFetchError
from verifier import Config, Database, event_counter, logger


class ServerDown(FailedFetch):
    def __init__(self, uri: str, next_try: float):
        self.next_try: float = next_try
        super().__init__(uri, "domain unavailable")


class BoundedFetcher:
    def __init__(self, max_connections: int, database: Database):
        self.fetcher: Fetcher = Fetcher(logger, timeout=Config.request_timeout)
        self.database: Database = database
        self.fetch_semaphore: asyncio.Semaphore = asyncio.Semaphore(max_connections)
        self.domains: Dict[str, dict] = {}
        self.temp_fails: Dict[str, float] = {}

    async def setup(self) -> None:
        await self.fetcher.setup()
        self.domains = await self.database.get_domains_dict()

    def reserve_time(self, domain: str) -> float:
        if domain not in self.domains:
            return time.time()
        d = self.domains[domain]
        d["reserved_time"] = max(
            time.time() + Config.request_timeout,
            d["next_try"],
            d.get("reserved_time", 0) + Config.request_timeout,
        )
        return d["reserved_time"]

    async def fetch_ap(self, uri: str) -> dict:
        domain = urlparse(uri).netloc
        if domain not in self.domains:
            self.domains[domain] = {"fails": 0, "next_try": time.time()}
        d = self.domains[domain]
        try:
            if time.time() < d["next_try"]:
                raise ServerDown(uri, d["next_try"])
            async with self.fetch_semaphore:
                data = await self.fetcher.fetch_ap(uri)
            if d["fails"] > 0:
                d["fails"] = 0
                d["next_try"] = 0
                await self.database.set_domain_state(domain, d["next_try"], d["fails"])
            return data
        except FailedFetch as e:
            if time.time() < d["next_try"]:
                raise ServerDown(uri, d["next_try"]) from e
            weight = 0.4
            if isinstance(e, TemporaryFetchError):
                weight = 1
                event_counter.on_event(event_counter.ACTOR_FETCH_TEMP_ERROR)
            else:
                event_counter.on_event(event_counter.ACTOR_FETCH_FAILED)
            logger.info(f"request to '{domain}' failed")
            self.temp_fails[domain] = self.temp_fails.get(domain, 0) + weight
            if self.temp_fails[domain] >= 5:
                logger.info(f"'{domain}' marked as down")
                if d["fails"] < len(Config.domain_retry_timers):
                    d["next_try"] = time.time() + Config.domain_retry_timers[d["fails"]]
                else:
                    d["next_try"] = INF_TIME_CONST
                d["fails"] += 1
                self.temp_fails[domain] = 0
                await self.database.set_domain_state(domain, d["next_try"], d["fails"])
            raise ServerDown(uri, d["next_try"]) from e

    async def shutdown(self) -> None:
        await self.fetcher.shutdown()
