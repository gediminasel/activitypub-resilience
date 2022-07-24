import hashlib
import json
from typing import Awaitable, Callable, List, Optional, Union
from urllib.parse import urlparse

from common.activity_streams import get_as_id
from common.webfinger import WebFinger, actor_from_as
from lookup.config import Config
from lookup.constants import ACTOR_TYPES, COLLECTION_TYPES, INFINITY_TIME
from lookup.database.database import Database
from lookup.database.objects import AsObjectType
from lookup.database.queue import QueueState
from lookup.logging import event_counter, logger


class ObjectHandler:
    def __init__(
        self,
        database: Database,
        on_id_found: Callable[[str, str, bool, Optional[str]], Awaitable[None]],
        webfinger: WebFinger,
    ) -> None:
        self.database = database
        self.on_id_found = on_id_found
        self.webfinger = webfinger

    async def handle(
        self,
        obj: Union[dict, str],
        trust_domain: Optional[str],
        priority: bool = False,
        aux: dict = None,
    ) -> None:
        return await self._handle(obj, trust_domain, priority, True, aux)

    async def _handle(
        self,
        obj: Union[dict, str],
        trust_domain: Optional[str],
        priority: bool = False,
        top_level: bool = False,
        aux: Optional[dict] = None,
    ) -> None:
        if isinstance(obj, str):
            return await self.on_id_found(
                obj, trust_domain, priority, (aux and json.dumps(aux)) or None
            )
        if not isinstance(obj, dict):
            return

        event_counter.on_event(event_counter.OBJECT_FOUND)

        oid = get_as_id(obj)
        typ = obj.get("type", None)
        if oid:
            parsed_id = urlparse(oid)
            if parsed_id.netloc == trust_domain and (
                top_level or (typ not in ACTOR_TYPES and typ not in COLLECTION_TYPES)
            ):
                old = await self.database.queue.get_element(oid)
                if old:
                    event_counter.all_time_fetched += 1
                    event_counter.queue_size -= 1
                    if typ in ACTOR_TYPES or typ in COLLECTION_TYPES:
                        cur_hash = hashlib.md5(
                            json.dumps(obj, sort_keys=True).encode()
                        ).hexdigest()
                        upd_period = min(
                            Config.min_update_period * 2, Config.max_update_period
                        )
                        if old["hash"]:
                            event_counter.on_event(event_counter.PAGE_REFETCHED)
                            if old["hash"] != cur_hash:
                                event_counter.on_event(event_counter.PAGE_UPDATED)
                                upd_period = max(
                                    Config.min_update_period, old["update_time"] / 2
                                )
                        await self.database.queue.update_state_time(
                            oid, QueueState.Fetched, upd_period, cur_hash
                        )
                    else:
                        await self.database.queue.update_state(oid, QueueState.Fetched)
                else:
                    # fetched by redirect
                    await self.database.queue.insert(
                        oid,
                        trust_domain,
                        trust_domain,
                        QueueState.Fetched,
                        Config.min_update_period
                        if typ in ACTOR_TYPES or typ in COLLECTION_TYPES
                        else INFINITY_TIME,
                        None,
                    )
            else:
                await self.on_id_found(oid, trust_domain, priority, None)
                return

        if typ in ACTOR_TYPES:
            await self._handle_actor(obj, trust_domain)
        elif typ in COLLECTION_TYPES:
            await self._handle_collection_or_page(obj, trust_domain, priority, aux)
        elif typ in ["Note"]:
            await self._handle_note(obj, trust_domain)
        elif typ in ["Create"]:
            await self._handle_activity(obj, trust_domain)
        else:
            logger.debug(f"Unknown type {typ}: {json.dumps(obj)}")

    async def _handle_actor(self, actor: dict, trusted_domain):
        oid = get_as_id(actor)
        if trusted_domain and oid:
            webfinger_actor = actor_from_as(actor, trusted_domain)
            webfinger_actor = await self.webfinger.resolve_actor_webfinger(
                webfinger_actor, oid
            )
            event_counter.on_event(event_counter.ACTOR_FOUND)
            if webfinger_actor is not None:
                await self.database.aliases.insert(webfinger_actor, oid)
            await self.database.objects.insert(
                oid, actor, AsObjectType.Actor, {"webfinger": webfinger_actor}
            )
            event_counter.actor_count += 1
        await self._handle_fields(
            actor, ["followers", "following"], trusted_domain, True
        )
        await self._handle_fields(actor, ["outbox"], trusted_domain)

    async def _handle_collection_or_page(
        self, coll: dict, trusted_domain, priority: bool, aux=None
    ):
        oid = get_as_id(coll)
        if trusted_domain and Config.archive_collections and oid:
            await self.database.objects.insert(oid, coll, AsObjectType.Feed)
        aux = {} if not aux else dict(aux)
        fields = ["items", "orderedItems"]
        if "colDir" in aux:
            fields.append(aux["colDir"])
        else:
            if "first" in coll or "next" in coll:
                fields.append("first" if "first" in coll else "next")
                aux["colDir"] = "next"
            else:
                fields.append("last")
                aux["colDir"] = "prev"
        items = coll.get("orderedItems", None) or coll.get("items", None)
        if items is None or not isinstance(items, list) or len(items) == 0:
            aux["empPag"] = aux.get("empPag", 0) + 1
            if aux["empPag"] > 2:
                return
        await self._handle_fields(coll, fields, trusted_domain, priority, aux)

    async def _handle_note(self, note: dict, trusted_domain):
        oid = get_as_id(note)
        if trusted_domain and Config.archive_notes and oid:
            await self.database.objects.insert(oid, note, AsObjectType.Other)
        await self._handle_fields(
            note, ["to", "cc", "attributedTo"], trusted_domain, True
        )
        await self._handle_fields(note, ["replies"], trusted_domain)

    async def _handle_activity(self, activity: dict, trusted_domain):
        await self._handle_fields(activity, ["actor", "object"], trusted_domain)

    async def _handle_fields(
        self,
        obj: dict,
        fields: List[str],
        trusted_domain,
        priority: bool = False,
        aux: Optional[dict] = None,
    ) -> None:
        for field in fields:
            if field not in obj:
                continue
            if isinstance(obj[field], list):
                for value in obj[field]:
                    await self._handle(value, trusted_domain, priority, False, aux)
            else:
                await self._handle(obj[field], trusted_domain, priority, False, aux)
