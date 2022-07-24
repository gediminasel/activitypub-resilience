import asyncio
import time
import traceback
from typing import List, Tuple

from lookup.config import Config
from lookup.constants import TRACE_LOG, log_trace
from lookup.database.domains import DomainState
from lookup.logging import logger


class Domain:
    def __init__(
        self,
        next_req: float = 0,
        fail_streak: int = 0,
        state: DomainState = DomainState.Unknown,
    ):
        self.next_req: float = next_req
        self.fail_streak: int = fail_streak
        self.temp_unreachable: bool = fail_streak > 0 and next_req > time.time()
        self.state: DomainState = state
        self.scheduled_items: int = 0
        self.failed_items: int = 0
        self.fetched_items: int = 0
        self.has_waiting_elements: bool = False
        self.not_scheduled: bool = False

    def is_temp_unreachable(self):
        if self.temp_unreachable:
            if self.next_req < time.time():
                self.temp_unreachable = False
            else:
                return True
        return False


class ScheduleQueue:
    def __init__(self, size: int):
        self.unavailable: List[Tuple[float, dict, Domain]] = []
        self.available_items: asyncio.Queue[
            Tuple[float, dict, Domain]
        ] = asyncio.Queue()
        self.size = size
        self.free_spaces = asyncio.Semaphore(size)
        self._track_waiting_task = asyncio.create_task(self._track_waiting())
        self.available: int = 0
        self.total: int = 0

    async def _track_waiting(self) -> None:
        waiting_items = []
        try:
            while True:
                waiting_items.extend(self.unavailable)
                self.unavailable = []

                waiting_items.sort(key=lambda x: x[0])
                new_waiting = []

                for t, uri, domain in waiting_items:
                    if (
                        domain.next_req < time.time()
                        or domain.temp_unreachable
                        or domain.state > DomainState.Unknown
                    ):
                        self.available_items.put_nowait((t, uri, domain))
                        self.available += 1
                    else:
                        new_waiting.append((t, uri, domain))

                waiting_items = new_waiting

                await asyncio.sleep(Config.domain_request_period / 4)
        except Exception as e:
            # something went very wrong
            traceback.print_exc()
            logger.exception(e)

    async def get_first_available(self) -> Tuple[dict, Domain]:
        cnt = 0
        while True:
            t, uri, domain = await self.available_items.get()
            self.available -= 1
            if (
                domain.next_req < time.time()
                or domain.temp_unreachable
                or domain.state > DomainState.Unknown
            ):
                self.free_spaces.release()
                if TRACE_LOG:
                    log_trace("A", self.available, self.total, cnt)
                self.total -= 1
                return uri, domain
            else:
                self.unavailable.append((t, uri, domain))
            cnt += 1

    async def put(self, uri: dict, domain: Domain):
        await self.free_spaces.acquire()
        self.available += 1
        self.total += 1
        self.available_items.put_nowait((time.time(), uri, domain))

    def stop(self):
        self._track_waiting_task.cancel()
