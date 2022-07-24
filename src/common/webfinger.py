import asyncio
import logging
import time
import traceback
import urllib.parse
from typing import Dict, Optional, Tuple, Union
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as XmlTree
from aiohttp import ClientError, ClientSession

from common.activity_streams import get_as_id
from common.constants import HOST_META_CONTENT_TYPE, WEBFINGER_CONTENT_TYPE


def get_webfinger_uri(actor: str) -> Optional[str]:
    usr_domain = split_actor(actor)
    if usr_domain is None:
        return None
    domain = urllib.parse.quote(usr_domain[1], safe="")
    return f"https://{domain}/.well-known/webfinger?resource={actor}"


def get_meta_uri(actor: str) -> Optional[str]:
    usr_domain = split_actor(actor)
    if usr_domain is None:
        return None
    domain = urllib.parse.quote(usr_domain[1], safe="")
    return f"https://{domain}/.well-known/host-meta"


def split_actor(actor: str) -> Optional[Tuple[str, str]]:
    if actor is None or not actor.startswith("acct:") or "@" not in actor:
        return None
    username, domain = actor[5:].split("@", 1)
    return username, domain


def find_link(webfinger: dict, rel: str) -> Optional[dict]:
    if "links" not in webfinger:
        return None
    for link in webfinger["links"]:
        if isinstance(link, dict) and "rel" in link and link["rel"] == rel:
            return link
    return None


def actor_from_as(
    activity_streams_actor: dict, domain: Optional[str] = None
) -> Optional[str]:
    if activity_streams_actor.get("preferredUsername", None) is None:
        return None
    domain = domain or urlparse(get_as_id(activity_streams_actor)).netloc
    return "acct:" + activity_streams_actor["preferredUsername"] + "@" + domain


class WebFinger:
    def __init__(self, session: ClientSession) -> None:
        self.session: ClientSession = session
        self.meta_cache: Dict[str, Tuple[float, Union[str, asyncio.Event, None]]] = {}

    async def get_webfinger_meta(self, meta_uri: str) -> Optional[Element]:
        try:
            async with self.session.get(
                meta_uri,
                headers={"Accept": HOST_META_CONTENT_TYPE},
            ) as response:
                if response.status != 200:
                    return None
                text = await response.text()
                return XmlTree.fromstring(text)
        except XmlTree.ParseError:
            return None
        except ClientError:
            return None
        except Exception as e:
            traceback.print_exc()
            logging.exception(e)
            return None

    async def resolve_webfinger_from_host_meta(self, actor: str) -> Optional[dict]:
        meta_uri = get_meta_uri(actor)
        cache = self.meta_cache.get(meta_uri, (0, None))
        if cache[0] + 3600 < time.time():
            if cache[0] == -1:
                await cache[1].wait()
                cache = self.meta_cache[meta_uri]
            else:
                event = asyncio.Event()
                self.meta_cache[meta_uri] = (-1, event)
                meta = await self.get_webfinger_meta(meta_uri)
                if meta is None:
                    return None
                template = None
                for child in meta:
                    if "rel" in child.attrib and child.attrib["rel"] == "lrdd":
                        template = child.attrib["template"]
                cache = (time.time(), template)
                self.meta_cache[meta_uri] = cache
                event.set()
        template = cache[1]
        if template is None:
            return None
        uri = template.replace("{uri}", actor)
        return await self.resolve_webfinger(actor, False, uri)

    async def resolve_webfinger(
        self, actor: str, use_meta=True, override_uri=None
    ) -> Optional[dict]:
        uri = override_uri or get_webfinger_uri(actor)
        if uri is None:
            return None
        try:
            if use_meta and get_meta_uri(actor) in self.meta_cache:
                return await self.resolve_webfinger_from_host_meta(actor)
            async with self.session.get(
                uri,
                headers={"Accept": WEBFINGER_CONTENT_TYPE},
            ) as response:
                if response.status == 404 and use_meta:
                    return await self.resolve_webfinger_from_host_meta(actor)
                if response.status != 200:
                    return None
                return dict(await response.json())
        except ClientError:
            return None
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            traceback.print_exc()
            logging.exception(e)
            return None

    async def get_actor_webfinger(self, actor: str) -> Optional[Tuple[str, str]]:
        for _ in range(2):
            if actor is None:
                return None
            webfinger = await self.resolve_webfinger(actor)
            if (
                webfinger is None
                or not isinstance(webfinger, dict)
                or webfinger.get("subject", None) is None
            ):
                return None
            if actor == webfinger["subject"]:
                self_link = find_link(webfinger, "self")
                if isinstance(self_link, dict) and "href" in self_link:
                    return actor, self_link["href"]
                return None
            actor = webfinger["subject"]

    async def resolve_actor_webfinger(
        self, actor: str, self_href: str
    ) -> Optional[str]:
        res = await self.get_actor_webfinger(actor)
        if res and res[1] == self_href:
            return res[0]
        return None
