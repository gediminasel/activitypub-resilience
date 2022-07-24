import asyncio
from functools import wraps


def async_test(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        future = f(*args, **kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(future)

    return wrapper


def raise_on_call(*_args, **_kwargs):
    raise AssertionError("logger.exception not called")
