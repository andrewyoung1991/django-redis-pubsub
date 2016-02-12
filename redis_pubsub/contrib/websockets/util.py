import asyncio
import functools as ft
import logging
import os

from django.conf import settings
from django.utils.module_loading import import_string

from aiohttp.web import WebSocketResponse, HTTPForbidden, Application

from redis_pubsub import REDIS_PUBSUB
from redis_pubsub.util import get_async_redis, SubscriptionManager


# a method that takes a token and returns an AUTH_USER_MODEL or None
authentication_method = import_string(REDIS_PUBSUB["tokenauth_method"])


logger = logging.getLogger(__name__)


def handle_auth(token):
    """ handles retrieving a user from a token
    """
    if token is None:
        raise HTTPForbidden(body=b"no token in request")

    user = authentication_method(token)
    if user is None:
        raise HTTPForbidden(body=b"invalid token")
    return user


def _clean_route(route):
    """ ensure that the route can be prefixed with os.path.join and ends with a slash if.
    """
    if route.startswith("/"):
        route = route[1:]
    route_ = os.path.join(REDIS_PUBSUB["websocket_url_prefix"], route)
    if not route_.endswith("/") and REDIS_PUBSUB["append_slash"]:  # pragma: no branch
        route_ = route_ + "/"
    if not route_.startswith("/"):
        route_ = "/" + route_
    return route_


def websocket(route, authenticate=False):
    """ a wrapper method for transforming a coroutine into a websocket handler.
    """
    def inner(func):
        func = asyncio.coroutine(func)

        @ft.wraps(func)
        @asyncio.coroutine
        def wrapper(request):
            params = request.GET
            kwargs = {}

            if authenticate:
                kwargs["user"] = handle_auth(params.get("token", None))

            ws = WebSocketResponse()
            try:
                yield from ws.prepare(request)
                yield from func(ws, params, **kwargs)
            except Exception as err:  # pragma: no cover
                logger.error(str(err))

            return ws

        # cleanup the route
        route_ = _clean_route(route)
        wrapper.route = ("GET", route_, wrapper)
        return wrapper
    return inner


def websocket_pubsub(route, authenticate=False):
    """ a wrapper method for transforming a coroutine into a websocket handler with
    a pubsub manager. if `authenticate=False` the signature of your coroutine should be
    `func(ws: WebSocketResponse, params: MultiDict, manager: SubscriptionManager)`
    otherwise an additional keywork argument is available, that being the authenticated
    user making the request.
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
                kwargs["user"] = handle_auth(params.get("token", None))

            redis_ = yield from get_async_redis()
            manager = SubscriptionManager(redis_)

            kwargs["manager"] = manager
            ws = WebSocketResponse()
            try:
                yield from ws.prepare(request)
                yield from func(ws, params, **kwargs)
                yield from manager.stop()
            except Exception as err:  # pragma: no cover
                logger.error(str(err))

            return ws

        # cleanup the route
        route_ = _clean_route(route)
        wrapper.route = ("GET", route_, wrapper)
        return wrapper
    return inner
