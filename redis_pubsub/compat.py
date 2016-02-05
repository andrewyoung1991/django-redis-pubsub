import asyncio

try:
    ensure_future = asyncio.ensure_future
except AttributeError:  # pragma: no cover
    ensure_future = asyncio.async
