import json
from typing import Optional
from unittest.mock import Mock

from aiohttp import ClientError


def mock_client_session(responses: Optional[dict]):
    session = Mock()

    # noinspection PyUnusedLocal
    def session_get(url, headers=None):
        class MockResponse:
            async def resp(self):
                if responses and url in responses:
                    content = responses[url]
                    resp = Mock()
                    if content is None:
                        resp.status = 404
                        return resp
                    resp.status = 200
                    if "__http_status_code" in content:
                        resp.status = content["__http_status_code"]
                        del content["__http_status_code"]

                    async def get_json():
                        return content

                    async def get_text():
                        if isinstance(content, str):
                            return content
                        return json.dumps(content)

                    resp.json = get_json
                    resp.text = get_text
                    return resp
                else:
                    raise ClientError()

            def __await__(self):
                return self.resp().__await__()

            async def __aenter__(self):
                return await self.resp()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        return MockResponse()

    session.get = Mock(side_effect=session_get)
    return session
