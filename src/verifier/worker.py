import asyncio
import json
import ssl
import time
import traceback
from asyncio import Lock
from typing import Dict, List, Optional, Tuple, TypedDict
from urllib.parse import urlparse

import aiohttp
import certifi
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from common.activity_streams import get_as_id
from common.constants import INF_TIME_CONST
from common.fetcher import FailedFetch
from common.signatures import Signer
from common.webfinger import WebFinger, actor_from_as
from verifier import Config
from verifier.bounded_fetcher import BoundedFetcher, ServerDown
from verifier.database import Database
from verifier.logging import event_counter, logger


class SignedActor(TypedDict):
    uri: str
    signature: str
    signature_time: int


class SignaturesBatch(TypedDict):
    signed_by: str
    signatures: List[SignedActor]


SignedActors = List[Tuple[dict, SignedActor]]


class Worker:
    def __init__(
        self,
        lookup_address: str,
        signer: Signer,
        database: Database,
        fetcher: BoundedFetcher,
    ) -> None:
        self.lookup: str = lookup_address
        self.signer: Signer = signer
        self.database: Database = database
        self.fetcher: BoundedFetcher = fetcher
        self.session: Optional[aiohttp.ClientSession] = None
        self.webfinger: Optional[WebFinger] = None

        self.queue_semaphore: asyncio.Semaphore = asyncio.Semaphore(Config.queue_size)
        self.next_domain_fetch: dict[str, Lock] = {}
        self.prev_domain_fetch: dict[str, Tuple[int, float]] = {}
        self.next_page: int = 0

        self.items_in_page: dict[int, dict[str, dict]] = {}
        self.tasks: Dict[int, asyncio.Task] = {}
        self.next_task: int = 0
        self.signed_actors: SignedActors = []
        self.enough_signatures: asyncio.Event = asyncio.Event()
        self.lookup_active: asyncio.Event = asyncio.Event()
        self.lookup_active.set()

    async def run(self) -> None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=Config.request_timeout),
            connector=aiohttp.TCPConnector(
                limit=Config.parallel_fetches, force_close=True, ssl=ssl_context
            ),
        )
        self.webfinger = WebFinger(self.session)
        self.tasks[-1] = asyncio.create_task(self.crawl_and_sign())
        self.tasks[-2] = asyncio.create_task(self.push_signed())
        self.next_task = 0

    async def push_signed(self):
        batch = Config.signature_batch_size
        while True:
            signatures: SignedActors = []
            try:
                if self.lookup_active.is_set():
                    try:
                        await asyncio.wait_for(
                            self.enough_signatures.wait(),
                            Config.signature_batch_timeout,
                        )
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(Config.signature_batch_timeout)

                signatures = self.signed_actors[:batch]
                self.signed_actors: SignedActors = self.signed_actors[batch:]
                if len(self.signed_actors) < batch:
                    self.enough_signatures.clear()

                if len(signatures) == 0:
                    continue

                data: SignaturesBatch = {
                    "signed_by": Config.actor_uri,
                    "signatures": [s[1] for s in signatures],
                }
                async with self.session.post(
                    f"{self.lookup}/actors/sign", json=data
                ) as r:
                    r.raise_for_status()
                    self.lookup_active.set()
                    event_counter.on_event(event_counter.BATCH_SUBMITTED)
                for actor, _ in signatures:
                    if "page" in actor:
                        await self.remove_from_queue(actor, actor["page"])
            except ClientError as e:
                self.lookup_active.clear()
                self.enough_signatures.set()
                self.signed_actors = signatures + self.signed_actors
                event_counter.on_event(event_counter.BATCH_SUBMIT_FAILED)
                for actor, _ in signatures:
                    if "page" in actor:
                        await self.remove_from_queue(actor, actor["page"])
                if isinstance(e, ClientResponseError):
                    logger.error(f"Lookup responded with {e.status}: {e.message}.")
                else:
                    logger.error("Submitting signatures to the lookup failed.")
                    logger.exception(e)
            except Exception as e:
                traceback.print_exc()
                # something is very bad
                for actor, _ in signatures:
                    if "page" in actor:
                        await self.remove_from_queue(actor, actor["page"])
                    fails = actor.get("fails", 0)
                    if fails < len(Config.actor_retry_timers):
                        next_fetch = time.time() + Config.actor_retry_timers[fails]
                    else:
                        next_fetch = INF_TIME_CONST
                    await self.database.add_to_queue(
                        self.lookup,
                        actor["uri"],
                        next_fetch,
                        fails + 1,
                        None,
                        None,
                    )
                logger.error("Submitting signatures to the lookup failed.")
                logger.exception(e)
                await asyncio.sleep(5)

    async def crawl_and_sign(self) -> None:
        self.next_page = await self.database.get_next_page(self.lookup)
        while True:
            try:
                actors_from_queue = await self.database.get_from_queue(
                    self.lookup, time.time(), Config.signature_batch_size
                )
                actors = []
                for a in actors_from_queue:
                    if a.get("json", None) is None:
                        try:
                            a["in_q"] = True
                            async with self.session.get(
                                f"{self.lookup}/get/{a['uri']}"
                            ) as r:
                                data = await r.json()
                                a["json"] = data["json"]
                                a["aux"] = data["aux"]
                        except Exception as e:
                            traceback.print_exc()
                            logger.exception(e)
                            fails = a.get("fails", 0)
                            next_fetch = time.time() + 60
                            await self.database.add_to_queue(
                                self.lookup, a["uri"], next_fetch, fails, None, None
                            )
                            continue
                    actors.append(a)
                    await self.database.set_active(self.lookup, a["uri"])
                async with self.session.get(
                    f"{self.lookup}/actors?page={self.next_page}"
                ) as r:
                    data = await r.json()
                    event_counter.on_event(event_counter.PAGE_FETCHED)
                for a in data["actors"]:
                    a["page"] = self.next_page
                actors.extend(data["actors"])
                if len(actors) != 0:
                    add_sign = asyncio.create_task(self.get_signatures(actors))
                    if len(self.tasks) > Config.queue_size / 2:
                        lookup_wait = asyncio.sleep(Config.lookup_request_period)
                        await asyncio.gather(lookup_wait, add_sign)
                    else:
                        await add_sign
                else:
                    lookup_wait = asyncio.sleep(Config.lookup_request_period)
                    await lookup_wait

                if data is not None and self.next_page + 1 < data["page_count"]:
                    # this page isn't last
                    self.next_page += 1
                    if len(self.items_in_page) == 0:
                        await self.database.set_next_page(self.lookup, self.next_page)
                else:
                    await asyncio.sleep(60)
            except aiohttp.ClientError as e:
                traceback.print_exc()
                logger.exception(e)
                await asyncio.sleep(5)
                continue
            except Exception as e:
                # something is very bad
                traceback.print_exc()
                logger.exception(e)
                await asyncio.sleep(5)

    async def get_signatures(self, actors: List[dict]) -> None:
        # print({a: len(b) for a, b in self.items_in_page.items()})
        # print(min((x for x in self.tasks.keys() if x >= 0), default=-1))
        oldest_task = min((x for x in self.tasks.keys() if x >= 0), default=-1)
        if (
            oldest_task >= 0
            and abs(oldest_task - self.next_task) > 5 * Config.queue_size
        ):
            await self.tasks[oldest_task]
        await self.lookup_active.wait()
        for actor in actors:
            wait_for = None
            await self.queue_semaphore.acquire()
            try:
                domain = urlparse(actor["uri"]).netloc
                if domain in self.prev_domain_fetch:
                    wait_for = self.prev_domain_fetch[domain]
                self.prev_domain_fetch[domain] = (self.next_task, 0)
                if "page" in actor:
                    page = actor["page"]
                    if page not in self.items_in_page:
                        self.items_in_page[page] = {}
                    self.items_in_page[page][actor["uri"]] = actor
                self.tasks[self.next_task] = asyncio.create_task(
                    self.get_signature(actor, self.next_task, wait_for)
                )
                self.next_task = (self.next_task + 1) % 1000000
            except Exception:
                traceback.print_exc()
                self.queue_semaphore.release()
                continue

    async def check_aux(self, real_actor: dict, actor_aux: dict) -> bool:
        if actor_aux.get("webfinger", None) is not None:
            webfinger = await self.webfinger.resolve_actor_webfinger(
                actor_from_as(real_actor), get_as_id(real_actor)
            )
            if actor_aux["webfinger"] != webfinger:
                return False
        return True

    async def get_signature(
        self, actor: dict, task_nr: int, wait_for: Tuple[int, float] = None
    ) -> float:
        if wait_for:
            task_id, next_rq = wait_for
            try:
                if task_id in self.tasks:
                    next_rq = await self.tasks[task_id]
                if next_rq is None:
                    next_rq = time.time() + Config.domain_request_period
                if next_rq > time.time():
                    await asyncio.sleep(next_rq - time.time())
            except asyncio.CancelledError:
                await asyncio.sleep(0)
            except Exception:
                traceback.print_exc()
        uri = None
        domain = None
        actor_json = actor["json"]
        actor_aux_json = actor["aux"]
        st = time.time()
        success = False
        try:
            uri = actor["uri"]
            domain = urlparse(uri).netloc
            actor["domain"] = domain
            real_actor = await self.fetcher.fetch_ap(uri)

            signature, signature_time = None, None
            if get_as_id(real_actor) == uri:
                actor_parsed: dict = json.loads(actor_json)
                actor_aux: dict = json.loads(actor_aux_json)
                if await self.check_aux(actor_parsed, actor_aux):
                    signature_time = int(time.time())
                    signature = await self.signer.compare_and_sign(
                        real_actor, actor_parsed, actor_aux, signature_time
                    )
            if signature is None or signature_time is None:
                await self.database.insert_difference(
                    self.lookup, uri, actor_json, json.dumps(real_actor), time.time()
                )
                event_counter.on_event(event_counter.ACTOR_INFO_MISMATCH)
                return time.time() + Config.domain_request_period

            event_counter.on_event(event_counter.ACTOR_SIGNED)
            signed_actor: SignedActor = {
                "uri": uri,
                "signature": signature,
                "signature_time": signature_time,
            }
            self.signed_actors.append((actor, signed_actor))
            success = True
            if len(self.signed_actors) >= Config.signature_batch_size:
                self.enough_signatures.set()
            return time.time() + Config.domain_request_period
        except asyncio.CancelledError:
            # for cleanup only!
            task_nr = None
            raise
        except ServerDown:
            event_counter.on_event(event_counter.ACTOR_FETCH_SKIPPED)
            if uri is not None:
                fails = actor.get("fails", 0)
                next_fetch = time.time() + Config.actor_retry_timers[max(fails - 1, 0)]
                next_fetch = max(next_fetch, self.fetcher.reserve_time(domain))
                await self.database.add_to_queue(
                    self.lookup, uri, next_fetch, fails, actor_json, actor_aux_json
                )
            return 0
        except FailedFetch:
            event_counter.on_event(event_counter.ACTOR_FETCH_FAILED)
            if uri is not None:
                fails = actor.get("fails", 0)
                if fails < len(Config.actor_retry_timers):
                    next_fetch = time.time() + Config.actor_retry_timers[fails]
                else:
                    next_fetch = INF_TIME_CONST
                await self.database.add_to_queue(
                    self.lookup, uri, next_fetch, fails + 1, actor_json, actor_aux_json
                )
        except Exception as e:
            traceback.print_exception(e)
            logger.exception(e)
        finally:
            if time.time() - st > 5:
                event_counter.on_event(event_counter.LONG_FETCH)
            if task_nr is not None:
                if actor.get("fails", 0) > 0 or actor.get("in_q", False):
                    await self.database.remove_from_queue(self.lookup, actor["uri"])
                if not success and actor and "page" in actor:
                    await self.remove_from_queue(actor, actor["page"])
                del self.tasks[task_nr]
                self.queue_semaphore.release()
                self.prev_domain_fetch[domain] = (
                    self.prev_domain_fetch[domain][0],
                    time.time() + Config.domain_request_period,
                )

    async def remove_from_queue(self, actor: dict, page: int):
        if page not in self.items_in_page:
            return
        del self.items_in_page[page][actor["uri"]]
        if len(self.items_in_page[page]) == 0 or (
            len(self.items_in_page[page]) <= 3 and len(self.items_in_page) >= 10
        ):
            for a in self.items_in_page[page].values():
                if "domain" in a:
                    a["in_q"] = True
                    await self.database.add_to_queue(
                        self.lookup,
                        a["uri"],
                        self.fetcher.reserve_time(a["domain"]),
                        a.get("fails", 0),
                        a["json"],
                        a["aux"],
                        1,
                    )
            del self.items_in_page[page]
            if len(self.items_in_page) > 0:
                await self.database.set_next_page(
                    self.lookup, min(self.items_in_page.keys())
                )
            else:
                await self.database.set_next_page(self.lookup, self.next_page)

    async def shutdown(self) -> None:
        for task in self.tasks.values():
            task.cancel()
        await self.session.close()
