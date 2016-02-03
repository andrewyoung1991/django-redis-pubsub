import asyncio

import pytest

from aiohttp import ws_connect, WSServerHandshakeError
from aiohttp.web import Application

from rest_framework.authtoken.models import Token

from redis_pubsub.contrib.websockets import websocket, websocket_pubsub


def test_websocket_wrapper():
    loop = asyncio.get_event_loop()

    @websocket()
    def handler(ws, params, **kwargs):
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        client = yield from ws_connect("http://localhost:9000")
        message = yield from client.receive()
        assert message.data == "hello, world!"

        yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


@pytest.mark.django_db
def test_websocket_pubsub_wrapper(subscription):
    loop = asyncio.get_event_loop()

    @websocket_pubsub()
    def handler(ws, params, **kwargs):
        reader = subscription.get_reader(kwargs["manager"])

        @reader.callback
        def send_message(channel_name, model):
            ws.send_str(model.name)
            return False

        listener = yield from reader.listen()
        yield from asyncio.gather(listener)

    @asyncio.coroutine
    def pub():
        yield from asyncio.sleep(1)  # wait a second for the listener to start
        return subscription.channel.publish(subscription.channel)

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        client = yield from ws_connect("http://localhost:9000")
        yield from pub()
        message = yield from client.receive()
        assert message.data == subscription.channel.name

        yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


def test_websocket_wrapper_authentication_error():
    loop = asyncio.get_event_loop()

    @websocket(authenticate=True)
    def handler(ws, params, **kwargs):
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        with pytest.raises(WSServerHandshakeError):
            client = yield from ws_connect("http://localhost:9000")
            yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


@pytest.mark.django_db
def test_websocket_wrapper_invalid_token_error():
    loop = asyncio.get_event_loop()

    @websocket(authenticate=True)
    def handler(ws, params, **kwargs):
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        with pytest.raises(WSServerHandshakeError):
            client = yield from ws_connect("http://localhost:9000?token=ooo")
            yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


@pytest.mark.django_db
def test_websocket_wrapper_valid_token(subscription):
    loop = asyncio.get_event_loop()
    token, _ = Token.objects.get_or_create(user=subscription.subscriber)
    token = token.key

    @websocket(authenticate=True)
    def handler(ws, params, **kwargs):
        assert kwargs["user"].id == subscription.subscriber.id
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        uri = "http://localhost:9000?token=" + token
        client = yield from ws_connect(uri)
        message = yield from client.receive()
        assert message.data == "hello, world!"
        yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


def test_websocket_pubsub_wrapper_authentication_error():
    loop = asyncio.get_event_loop()

    @websocket_pubsub(authenticate=True)
    def handler(ws, params, **kwargs):
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        with pytest.raises(WSServerHandshakeError):
            client = yield from ws_connect("http://localhost:9000")
            yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


@pytest.mark.django_db
def test_websocket_pubsub_wrapper_invalid_token_error():
    loop = asyncio.get_event_loop()

    @websocket_pubsub(authenticate=True)
    def handler(ws, params, **kwargs):
        ws.send_str("hello, world!")

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        with pytest.raises(WSServerHandshakeError):
            client = yield from ws_connect("http://localhost:9000?token=ooo")
            yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))


@pytest.mark.django_db
def test_websocket_pubsub_wrapper_valid_token(subscription):
    loop = asyncio.get_event_loop()
    token, _ = Token.objects.get_or_create(user=subscription.subscriber)
    token = token.key

    @websocket_pubsub(authenticate=True)
    def handler(ws, params, **kwargs):
        assert kwargs["user"].id == subscription.subscriber.id
        reader = subscription.get_reader(kwargs["manager"])

        @reader.callback
        def send_message(channel_name, model):
            ws.send_str(model.name)
            return False

        listener = yield from reader.listen()
        yield from asyncio.gather(listener)

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route("GET", "/", handler)
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def pub():
        yield from asyncio.sleep(1)  # wait a second for the listener to start
        return subscription.channel.publish(subscription.channel)

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        uri = "http://localhost:9000?token=" + token
        client = yield from ws_connect(uri)

        yield from pub()
        message = yield from client.receive()
        assert message.data == subscription.channel.name
        yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))
