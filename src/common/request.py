from aiohttp import web


def get_int_query_param(request: web.Request, name: str, error_msg: str) -> int:
    val = request.query.get(name)

    try:
        val = int(val)
    except (TypeError, ValueError):
        val = None

    if val is None:
        raise web.HTTPBadRequest(text=error_msg)
    return val


def get_str_query_param(request: web.Request, name: str, error_msg: str) -> str:
    val = request.query.get(name)
    if val is None:
        raise web.HTTPBadRequest(text=error_msg)
    return val
