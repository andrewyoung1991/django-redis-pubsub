import asyncio
import functools as ft

from aiohttp.web import WebSocketResponse, HTTPForbidden

from rest_framework.authtoken.models import Token

from redis_pubsub.util import get_async_redis, SubscriptionManager


def websocket(authenticate=False):
    """
    """
    def inner(func):
        func = asyncio.coroutine(func)

        @ft.wraps(func)
        @asyncio.coroutine
        def wrapper(request):
            params = request.GET
            kwargs = {}

            token = params.get("token", None)
            if authenticate:
                if token is None:
                    raise HTTPForbidden(body=b"no token in request")
                try:
                    kwargs["user"] = Token.objects.get(key=token).user
                except Token.DoesNotExist:
                    raise HTTPForbidden(body=b"invalid token")

            ws = WebSocketResponse()
            yield from ws.prepare(request)
            yield from func(ws, params, **kwargs)
            return ws
        return wrapper
    return inner


def websocket_pubsub(authenticate=False):
    def inner(func):
        func = asyncio.coroutine(func)

        @ft.wraps(func)
        @asyncio.coroutine
        def wrapper(request):
            params = request.GET
            kwargs = {}

            token = params.get("token", None)
            if authenticate:
                if token is None:
                    raise HTTPForbidden(body=b"no token in request")
                try:
                    kwargs["user"] = Token.objects.get(key=token).user
                except Token.DoesNotExist:
                    raise HTTPForbidden(body=b"invalid token")

            ws = WebSocketResponse()
            yield from ws.prepare(request)

            redis_ = yield from get_async_redis()
            manager = SubscriptionManager(redis_)

            kwargs["manager"] = manager
            yield from func(ws, params, **kwargs)
            yield from manager.stop()

            return ws
        return wrapper
    return inner
