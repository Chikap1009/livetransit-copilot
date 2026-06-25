"""Shared async entrypoint runner.

psycopg's async mode requires a SelectorEventLoop; Windows defaults to a
ProactorEventLoop. On Linux (e.g. inside Docker) the default already works,
so this is a no-op there. Used by the poller and processor workers.
"""
import asyncio
import sys


def run(coro):
    if sys.platform == "win32":
        return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coro)
