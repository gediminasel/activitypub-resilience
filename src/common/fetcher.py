import asyncio
import json
import logging
import ssl
import traceback
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import certifi
from aiohttp import ClientTimeout

from common.constants import ACCEPTABLE_CONTENT_TYPES, HIGHLY_RELIABLE_SITES


class FailedFetch(Exception):
    def __init__(self, uri, message):
        self.uri = uri
        self.message = message
        super().__init__(f"Fetching {uri} failed: {message}")


class TemporaryFetchError(FailedFetch):
    def __init__(self, uri, message):
        self.message = message
        super().__init__(uri, f"{message}, retry later")


class Fetcher:
    def __init__(
        self,
        logger: logging.Logger,
        limit: int = 100,
        debug: bool = False,
        timeout: float = 20,
    ) -> None:
        self.logger = logger
        self._limit = limit
        self._timeout = timeout
        self._debug = debug
        self.session: Optional[aiohttp.ClientSession] = None

    async def check_connection(self):
        for url in HIGHLY_RELIABLE_SITES:
            try:
                async with self.session.get(url):
                    return True
            except Exception as e:
                # connection failed
                logging.exception(e)
        return False

    async def setup(self) -> None:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session = aiohttp.ClientSession(
            timeout=ClientTimeout(total=self._timeout, connect=5),
            connector=aiohttp.TCPConnector(
                limit=self._limit, force_close=True, ssl=ssl_context
            ),
        )

    async def shutdown(self) -> None:
        await self.session.close()

    async def fetch_ap(self, uri: str) -> dict:
        if not isinstance(uri, str):
            raise TypeError()
        if uri.startswith("//"):
            uri = "https:" + uri
        try:
            parsed_uri = urlparse(uri)
            if parsed_uri.scheme != "https" and not self._debug:
                raise FailedFetch(uri, "only https scheme is supported")
            if (
                parsed_uri.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]
                and not self._debug
            ):
                raise FailedFetch(uri, "local requests aren't supported")
            async with self.session.get(
                uri,
                headers={"Accept": ACCEPTABLE_CONTENT_TYPES},
            ) as response:
                if response.status == 401:
                    raise FailedFetch(uri, "Private resource")
                if response.status == 403:
                    raise FailedFetch(uri, "Private resource")
                if response.status == 404:
                    raise FailedFetch(uri, "not found")
                elif response.status == 429:
                    raise TemporaryFetchError(uri, "rate limit exceeded")
                elif response.status // 100 == 5:
                    raise TemporaryFetchError(uri, f"server error {response.status}")
                elif response.status != 200:
                    raise FailedFetch(uri, f"response code {response.status}")

                obj = await response.json()
                if not obj:
                    raise FailedFetch(uri, "object not found")
                if not isinstance(obj, dict):
                    raise FailedFetch(uri, "expected json dictionary")
                return obj
        except AssertionError:
            raise FailedFetch(uri, "probably uri parsing failed??")
        except asyncio.TimeoutError:
            raise TemporaryFetchError(uri, "timeout")
        except aiohttp.ServerDisconnectedError:
            raise TemporaryFetchError(uri, "server disconnected")
        except aiohttp.ClientConnectorError:
            raise TemporaryFetchError(uri, "failed to connect")
        except ConnectionResetError:
            raise TemporaryFetchError(uri, "connection was reset")
        except aiohttp.ClientOSError:
            raise TemporaryFetchError(uri, "client os error")
        except aiohttp.ClientPayloadError:
            raise FailedFetch(uri, "payload error: wrong http version?")
        except aiohttp.InvalidURL:
            raise FailedFetch(uri, "invalid URL")
        except aiohttp.ContentTypeError:
            raise TemporaryFetchError(uri, "site return unexpected content type")
        except aiohttp.TooManyRedirects:
            raise FailedFetch(uri, "too many redirects")
        except json.JSONDecodeError:
            raise TemporaryFetchError(uri, "can't parse returned json")
        except UnicodeDecodeError:
            raise FailedFetch(uri, "unknown character in json")
        except aiohttp.ClientError:
            raise TemporaryFetchError(uri, "client error")
        except OSError:
            raise TemporaryFetchError(uri, "os error")
        except FailedFetch:
            raise
        except Exception as e:
            # something went very wrong
            traceback.print_exc()
            self.logger.error(f"Fetching {uri} failed with exception")
            self.logger.exception(e)
            raise FailedFetch(uri, "unknown error") from e
