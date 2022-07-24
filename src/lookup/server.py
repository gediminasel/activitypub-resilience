import json
import logging
import time
from typing import Optional, Tuple

from aiohttp import web

from common.constants import AS_JSON_CONTENT_TYPE, HTML_CONTENT_TYPE, JSON_CONTENT_TYPE
from common.request import get_int_query_param, get_str_query_param
from common.signatures import Verifier
from lookup import Crawler, event_counter
from lookup.config import Config
from lookup.database.database import Database
from lookup.database.domains import DomainState
from lookup.database.objects import AsObjectType
from lookup.logging import logger
from lookup.signatures import add_signatures


class WebServer:
    def __init__(self, database: Database, crawler: Optional[Crawler] = None):
        self.database: Database = database
        self.crawler: Optional[Crawler] = crawler
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.sign_verifier: Verifier = Verifier(1)

        self.last_stats_cache: Tuple[float, Optional[dict]] = (0, None)

    async def get_handler(self, request: web.Request):
        uri = request.match_info["uri"]
        as_object = await self.database.objects.get_as_object(uri)
        if as_object is None:
            uri = await self.database.aliases.get_id(uri)
            if uri is not None:
                as_object = await self.database.objects.get_as_object(uri)
        if as_object is None:
            event_counter.on_event(event_counter.GET_OBJECT_NOT_FOUND)
            return web.HTTPNotFound()
        if as_object["type"] == AsObjectType.Actor:
            signatures = await self.database.signatures.get_object_signatures(
                as_object["num"]
            )
            as_object["key_signatures"] = []
            for s in signatures:
                as_object["key_signatures"].append(
                    {
                        "signed_by": self.database.verifiers.get_by_id(s[0])["uri"],
                        "signature": s[1],
                        "signature_time": s[2],
                    }
                )
        event_counter.on_event(event_counter.GET_OBJECT_SERVED)
        return web.Response(
            text=json.dumps(as_object), content_type=AS_JSON_CONTENT_TYPE
        )

    async def status_handler(self, _request: web.Request):
        if self.last_stats_cache[0] < time.time() - 1:
            stats = await self.database.stats.get_last()
            self.last_stats_cache = (
                time.time(),
                None if stats is None else json.loads(stats["json"]),
            )

        return web.Response(
            text=json.dumps(
                {
                    "total": event_counter.get_total_stats(),
                    "current": event_counter.get_stats(),
                    "previous": self.last_stats_cache[1],
                },
                sort_keys=True,
            ),
            content_type=JSON_CONTENT_TYPE,
        )

    async def actors_page_handler(self, request: web.Request):
        page_nr = get_int_query_param(request, "page", "Specify page number")
        if page_nr < 0:
            raise web.HTTPBadRequest(text="Page number must be non-negative")

        page = await self.database.objects.get_objects_page(AsObjectType.Actor, page_nr)
        page_cnt = await self.database.objects.get_page_count()
        event_counter.on_event(event_counter.ACTOR_PAGE_SERVED)
        return web.Response(
            text=json.dumps({"actors": page, "page_count": page_cnt}),
            content_type=JSON_CONTENT_TYPE,
        )

    async def actors_to_sign_handler(self, request: web.Request):
        verifier_uri = get_str_query_param(request, "verifier", "Specify verifier uri")
        verifier_id = self.database.verifiers.get_by_uri(verifier_uri)["id"]

        nums = await self.database.signatures.get_not_signed(verifier_id, 100)
        page = [await self.database.objects.get_as_object_by_num(num) for num in nums]
        event_counter.on_event(event_counter.ACTORS_TO_SIGN_SERVED)
        return web.Response(
            text=json.dumps({"actors": page}),
            content_type=JSON_CONTENT_TYPE,
        )

    async def sign_page_handler(self, request: web.Request):
        data = await request.json()
        if "signed_by" not in data or "signatures" not in data:
            raise web.HTTPBadRequest(text="Missing signed_by or signatures")

        signed_by = data["signed_by"]
        signer = self.database.verifiers.get_by_uri(signed_by)
        if signer is None:
            raise web.HTTPForbidden()
        signatures = data["signatures"]
        if not isinstance(signatures, list):
            raise web.HTTPBadRequest(text="Signatures must be an array")

        await add_signatures(self.sign_verifier, self.database, signer, signatures)

        return web.HTTPOk()

    async def main_handler(self, _request: web.Request):
        actor_cnt = event_counter.actor_count
        queue_sz = event_counter.queue_size
        uris_fetched = event_counter.all_time_fetched

        if self.crawler is not None:
            domains = self.crawler.domains
        else:
            domains = {}

        waiting_domains_sz = sum(
            1
            for d in domains.values()
            if d.state <= DomainState.Unknown and d.has_waiting_elements
        )
        waiting_reachable = sum(
            1
            for d in domains.values()
            if d.state <= DomainState.Unknown
            and d.fail_streak == 0
            and d.has_waiting_elements
        )
        domains_sz = len(domains)
        unreachable_cnt = sum(
            1
            for d in domains.values()
            if d.fail_streak > 0 and d.state <= DomainState.Unknown
        )
        blocked_cnt = sum(1 for d in domains.values() if d.state > DomainState.Unknown)

        return web.Response(
            text=f"""
<html>
<head></head>
<body>
<h1>ActivityPub users lookup server</h1>
<p>
You can query cached copies of ActivityPub users using this url template:
<code>/get/[user id]</code>.
</p>
<h2>Stats</h2>
<table>
<tr>
<td>Actors discovered</td>
<th>{actor_cnt}</th>
</tr>
<tr>
<td>URIs in queue</td>
<th>{queue_sz} (from {waiting_domains_sz} domains, {waiting_reachable} alive)</th>
</tr>
<tr>
<td>Domains found</td>
<th>{domains_sz} ({unreachable_cnt} currently unreachable, {blocked_cnt} blocked)</th>
</tr>
<tr>
<td>URIs fetched</td>
<th>{uris_fetched}</th>
</tr>
</table>
<p>
For any questions please reach out to <a href="https://lelesius.eu/">lelesius.eu</a>
</p>
</body>
</html>""",
            content_type=HTML_CONTENT_TYPE,
        )

    async def run(self):
        self.app = web.Application()
        self.app.router.add_route("GET", "/get/{uri:.*}", self.get_handler)
        self.app.router.add_route("GET", "/actors", self.actors_page_handler)
        self.app.router.add_route("GET", "/actors/to_sign", self.actors_to_sign_handler)
        self.app.router.add_route("POST", "/actors/sign", self.sign_page_handler)
        self.app.router.add_route("GET", "/status", self.status_handler)
        self.app.router.add_route("GET", "/", self.main_handler)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, Config.web_host, Config.web_port)
        await self.site.start()
        if logger.level <= logging.INFO:
            logger.info(
                f"Started lookup web server at {Config.web_host}:{Config.web_port}"
            )
        else:
            print(f"Started lookup web server at {Config.web_host}:{Config.web_port}")

    async def shutdown(self):
        await self.site.stop()
        await self.runner.shutdown()
