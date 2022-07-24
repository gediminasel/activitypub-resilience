import json
from typing import Optional, Tuple

from aiohttp import web

from common.constants import AS_JSON_CONTENT_TYPE, JSON_CONTENT_TYPE
from common.signatures import Signer
from verifier.config import Config
from verifier.logging import event_counter, logger


class WebServer:
    def __init__(self, signer: Signer):
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.signer: Signer = signer

        self.actor = {
            "type": "Application",
            "id": Config.actor_uri,
            "name": Config.actor_name,
            "publicKey": {
                "id": f"{Config.actor_uri}#main-key",
                "owner": Config.actor_uri,
                "publicKeyPem": self.signer.key.public_key()
                .export_key(format="PEM")
                .decode(),
            },
        }

        self.last_stats_cache: Tuple[float, Optional[dict]] = (0, None)

    async def get_key_handler(self, _request: web.Request):
        return web.Response(
            text=json.dumps(self.actor), content_type=AS_JSON_CONTENT_TYPE
        )

    async def get_status_handler(self, _request: web.Request):
        return web.Response(
            text=json.dumps(
                {
                    "total": event_counter.get_total_stats(),
                    "current": event_counter.get_stats(),
                },
                sort_keys=True,
            ),
            content_type=JSON_CONTENT_TYPE,
        )

    async def run(self):
        self.app = web.Application()
        self.app.router.add_route("GET", Config.status_path, self.get_status_handler)
        self.app.router.add_route("GET", Config.actor_key_path, self.get_key_handler)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, Config.web_host, Config.web_port)
        await self.site.start()
        logger.info(
            f"Serving verifier key at {Config.web_host}:{Config.web_port}{Config.actor_key_path} "
            f"and it should be accessible at {Config.actor_uri}"
        )

    async def shutdown(self):
        await self.site.stop()
        await self.runner.shutdown()
