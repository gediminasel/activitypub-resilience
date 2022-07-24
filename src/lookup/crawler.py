import asyncio
import json
import random
import time
import traceback
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from common.activity_streams import get_as_id
from common.fetcher import FailedFetch, Fetcher, TemporaryFetchError
from common.webfinger import WebFinger
from lookup.config import Config
from lookup.constants import FETCH_RETRY_TIMERS, INFINITY_TIME, TRACE_LOG, log_trace
from lookup.database.database import Database
from lookup.database.domains import DomainState
from lookup.database.queue import QueueState
from lookup.logging import event_counter, logger
from lookup.obj_handler import ObjectHandler
from lookup.schedule_queue import Domain, ScheduleQueue


class Crawler:
    def __init__(self, database: Database, fetcher: Fetcher):
        self.database: Database = database
        self.fetcher: Fetcher = fetcher
        self.webfinger: WebFinger = WebFinger(self.fetcher.session)
        self.items_to_explore: Optional[ScheduleQueue] = None
        self.domains: Dict[str, Domain] = {}
        self.not_scheduled_domains: List[str] = []
        self.tasks: List[asyncio.Task] = []
        self.object_handler: Optional[ObjectHandler] = None
        self.internet: Optional[asyncio.Event] = None
        self.active: int = 0

    async def run(self, start_uris: Iterable[str] = None):
        self.items_to_explore = ScheduleQueue(Config.max_queue_size)
        self.internet = asyncio.Event()
        self.object_handler = ObjectHandler(
            self.database, self.add_if_not_visited, self.webfinger
        )

        for uri in start_uris:
            parse = urlparse(uri)
            if not parse.netloc:
                webf = await self.webfinger.get_actor_webfinger(uri)
                if webf:
                    uri = webf[1]
                    parse = urlparse(uri)
            if parse.netloc:
                await self.add_if_not_visited(uri, parse.netloc, True)
            else:
                logger.warning(f"'{uri}' isn't a valid URI nor webfinger. Skipping it.")

        for domain in await self.database.domains.get_all():
            self.domains[domain["domain"]] = Domain(
                domain["next_req"], domain["fail_streak"], domain["state"]
            )

        for domain_name in await self.database.queue.get_waiting_domains():
            if domain_name not in self.domains:
                self.domains[domain_name] = Domain()
            domain = self.domains[domain_name]
            if domain.state <= DomainState.Unknown:
                domain.has_waiting_elements = True
                if not domain.not_scheduled:
                    self.not_scheduled_domains.append(domain_name)
                    domain.not_scheduled = True

        self.tasks.append(asyncio.create_task(self._process_queue()))
        self.tasks.append(asyncio.create_task(self._process_update()))
        self.tasks.extend(
            [asyncio.create_task(self._fetch()) for _ in range(Config.parallel_fetches)]
        )
        if Config.check_for_internet_access > 0:
            self.tasks.append(asyncio.create_task(self._check_connection()))
        else:
            self.internet.set()

    async def add_if_not_visited(
        self, uri: str, found_in: str, priority: bool = False, aux: dict = None
    ) -> None:
        if uri in ["https://www.w3.org/ns/activitystreams#Public"]:
            return
        parsed = urlparse(uri)
        domain: str = parsed.netloc
        if domain not in self.domains:
            self.domains[domain] = Domain()
        state = QueueState.WaitingPriority if priority else QueueState.Waiting
        if self.domains[domain].state >= DomainState.Unreachable:
            state = QueueState.Blocked
        if await self.database.queue.insert(
            uri,
            domain,
            found_in,
            state,
            Config.min_update_period if priority else INFINITY_TIME,
            aux,
        ):
            if self.domains[domain].state < DomainState.Unreachable:
                self.domains[domain].has_waiting_elements = True
                if (
                    self.domains[domain].scheduled_items == 0
                    and not self.domains[domain].not_scheduled
                ):
                    self.not_scheduled_domains.append(domain)
                    self.domains[domain].not_scheduled = True
            event_counter.on_event(event_counter.NEW_URI_FOUND)
            event_counter.queue_size += 1

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        self.items_to_explore.stop()

    async def _check_connection(self):
        while True:
            if await self.fetcher.check_connection():
                self.internet.set()
            else:
                logger.warning("No internet connection!")
                self.internet.clear()
            await asyncio.sleep(Config.check_for_internet_access)

    def _is_domain_ok_for_scheduling(self, domain_name: str, domain: Domain) -> bool:
        if domain.is_temp_unreachable():
            return False
        if domain.state > DomainState.Unknown:
            if domain.not_scheduled:
                self.not_scheduled_domains.remove(domain_name)
                domain.not_scheduled = False
            domain.has_waiting_elements = False
            return False
        if domain.scheduled_items > 0 and domain.not_scheduled:
            self.not_scheduled_domains.remove(domain_name)
            domain.not_scheduled = False
        if domain.scheduled_items >= Config.max_in_queue_per_domain:
            return False
        return True

    def _choose_random_domain(self) -> Optional[str]:
        random_domain_name = None
        tries = 5
        while random_domain_name is None and tries > 0:
            tries -= 1
            if len(self.not_scheduled_domains) == 0:
                return None
            random_domain_name = random.choice(self.not_scheduled_domains)
            domain = self.domains[random_domain_name]
            if not self._is_domain_ok_for_scheduling(random_domain_name, domain):
                random_domain_name = None
        return random_domain_name

    async def _schedule_items(self, items):
        for item in items:
            uri = item["uri"]
            domain_name = urlparse(uri).netloc
            if domain_name not in self.domains:
                self.domains[domain_name] = Domain()
            domain = self.domains[domain_name]

            if domain.state > DomainState.Unknown:
                await self.database.queue.update_state(uri, QueueState.Blocked)
                event_counter.queue_size -= 1
                continue

            if domain.is_temp_unreachable():
                continue
            if domain.scheduled_items >= Config.max_in_queue_per_domain:
                continue

            if domain.scheduled_items == 0 and domain.not_scheduled:
                self.not_scheduled_domains.remove(domain_name)
                domain.not_scheduled = False
            domain.scheduled_items += 1

            await self.database.queue.update_state(uri, -item["state"])
            await self.items_to_explore.put(item, domain)

    async def _schedule_random_from_all(self):
        items = await self.database.queue.get_random(Config.scheduler_chunk)
        if len(items) < min(Config.scheduler_chunk, 200):
            if len(items) == 0:
                logger.warning("Sleeping because there isn't much to do :(")
            await asyncio.sleep(Config.domain_request_period / (len(items) + 1))
        await self._schedule_items(items)

    async def _schedule_random_from_domain(self):
        domains = []
        random.shuffle(self.not_scheduled_domains)
        for domain_name in self.not_scheduled_domains:
            if self._is_domain_ok_for_scheduling(
                domain_name, self.domains[domain_name]
            ):
                domains.append(domain_name)
            if len(domains) >= Config.domain_chunk:
                break
        if not domains:
            return await self._schedule_random_from_all()
        # noinspection PyTypeChecker
        domain_items: Tuple[List[dict]] = await asyncio.gather(
            *(
                self.database.queue.get_random_from_domain(
                    domain_name, Config.choose_from_domain_queue
                )
                for domain_name in domains
            )
        )
        items = []
        for d_items, domain_name in zip(domain_items, domains):
            cnt = 0
            for item in d_items:
                cnt += 1
                if item["state"] == QueueState.Waiting:
                    break
                items.append(item)
            if cnt == 0:
                domain = self.domains[domain_name]
                domain.has_waiting_elements = False
                if domain.not_scheduled:
                    domain.not_scheduled = False
                    self.not_scheduled_domains.remove(domain_name)
        if TRACE_LOG:
            log_trace("CI", len(items))

        await self._schedule_items(items)

    async def _schedule_random_items(self):
        if TRACE_LOG:
            log_trace(
                "SR",
                self.items_to_explore.available,
                self.items_to_explore.total,
                len(self.not_scheduled_domains),
            )
        if (
            random.random() > Config.prob_choose_from_domains
            or len(self.not_scheduled_domains) == 0
        ):
            await self._schedule_random_from_all()
        else:
            await self._schedule_random_from_domain()

    async def _process_update(self):
        while True:
            try:
                if TRACE_LOG:
                    log_trace(
                        "U",
                        time.time(),
                        self.items_to_explore.available,
                        self.items_to_explore.total,
                    )
                await self.database.queue.set_next_to_update()
                await asyncio.sleep(2)

            except Exception as e:
                # something went very wrong
                traceback.print_exc()
                logger.exception(e)
                await asyncio.sleep(2)

    async def _process_queue(self):
        while True:
            try:
                if TRACE_LOG:
                    log_trace(
                        "S",
                        time.time(),
                        self.items_to_explore.available,
                        self.items_to_explore.total,
                    )
                await self._schedule_random_items()
                if self.items_to_explore.total > Config.max_queue_size / 2:
                    await asyncio.sleep(0.2)

            except Exception as e:
                # something went very wrong
                traceback.print_exc()
                logger.exception(e)
                await asyncio.sleep(2)

    async def _fetch_single(self, item, domain: Domain):
        uri = item["uri"]
        parsed_uri = urlparse(uri)
        domain_name = parsed_uri.netloc
        if domain.state > DomainState.Unknown:
            await self.database.queue.update_state(uri, QueueState.Blocked)
            event_counter.queue_size -= 1
            return
        if domain.is_temp_unreachable():
            await self.database.queue.update_state(uri, item["state"])
            return

        old_next_req = domain.next_req
        old_fail_streak = domain.fail_streak
        try:
            domain.next_req = max(
                domain.next_req, time.time() + Config.domain_request_period
            )
            self.active += 1
            if TRACE_LOG:
                log_trace("F", domain_name, time.time(), self.active)
            obj = await self.fetcher.fetch_ap(uri)
            if TRACE_LOG:
                log_trace("FF", domain_name, time.time(), uri, self.active)
            event_counter.on_event(event_counter.PAGE_FETCHED)

            domain.fetched_items += 1
            if domain.fail_streak > 0:
                domain.fail_streak = 0
                await self.database.domains.update(
                    domain_name, domain.fail_streak, domain.next_req
                )

            oid = get_as_id(obj)
            if oid is not None and oid != uri:
                # don't visit via this redirect, use object id instead
                await self.database.queue.update_state(uri, QueueState.Redirected)
                event_counter.queue_size -= 1

                received_netloc = urlparse(oid).netloc
                if received_netloc != parsed_uri.netloc:
                    await self.add_if_not_visited(
                        oid, domain_name, item["state"] == QueueState.WaitingPriority
                    )
                    return
                else:
                    await self.database.aliases.insert(uri, oid)
            await self.object_handler.handle(
                obj,
                domain_name,
                item["state"] == QueueState.WaitingPriority,
                (item["aux"] and json.loads(item["aux"])) or None,
            )

        except TemporaryFetchError:
            event_counter.on_event(event_counter.PAGE_FETCH_TEMP_ERROR)
            if TRACE_LOG:
                log_trace("FTE", domain_name, time.time(), uri)

            if time.time() < old_next_req or old_fail_streak != domain.fail_streak:
                return

            if domain.fail_streak >= len(FETCH_RETRY_TIMERS):
                domain.state = DomainState.Unreachable
                await self.database.domains.update_state(domain_name, domain.state)
                await self.database.queue.update_state(uri, QueueState.Failed)
                event_counter.queue_size -= 1
            else:
                domain.next_req = time.time() + FETCH_RETRY_TIMERS[domain.fail_streak]
                domain.fail_streak += 1
                domain.temp_unreachable = True
                await self.database.domains.update(
                    domain_name, domain.fail_streak, domain.next_req
                )
                await self.database.queue.update_state(uri, item["state"])

        except FailedFetch:
            if TRACE_LOG:
                log_trace("FE", domain_name, time.time(), uri)

            event_counter.on_event(event_counter.PAGE_FETCH_FAILED)
            await self.database.queue.update_state(uri, QueueState.Failed)
            event_counter.queue_size -= 1

            domain.failed_items += 1
            if (
                domain.failed_items >= 50
                and domain.failed_items / (domain.failed_items + domain.fetched_items)
                > 0.5
            ):
                domain.state = DomainState.AutoBlocked
                await self.database.domains.update_state(domain_name, domain.state)
        finally:
            self.active -= 1

    async def _fetch(self):
        while True:
            uri = None
            try:
                await self.internet.wait()
                item, domain = await self.items_to_explore.get_first_available()
                uri = item["uri"]
                parsed_uri = urlparse(uri)
                domain_name = parsed_uri.netloc
                domain.scheduled_items -= 1
                if domain.scheduled_items == 0 and not domain.not_scheduled:
                    if domain.has_waiting_elements:
                        self.not_scheduled_domains.append(domain_name)
                        domain.not_scheduled = True
                await self._fetch_single(item, domain)

            except Exception as e:
                # something went terribly wrong
                logger.error("Exception while fetching" + (" " + uri if uri else ""))
                logger.exception(e)
                await asyncio.sleep(3)
