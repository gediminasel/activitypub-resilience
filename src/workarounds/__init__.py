import asyncio
import gc
import types


def run_in_event_loop_windows_workaround(run, cleanup):
    """
    workaround for `AttributeError: 'NoneType' object has no attribute 'send'`
    and `RuntimeError: Event loop is closed`
    when terminating application.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        pass
    finally:
        loop._check_closed = types.MethodType(lambda x: None, loop)
        gc.collect()
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except KeyboardInterrupt:
            pass
        loop.run_until_complete(cleanup())
        loop.stop()
        loop.close()
