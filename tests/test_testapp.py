import asyncio

import pytest
from model_mommy import mommy

from aiohttp import ws_connect, WSServerHandshakeError
from aiohttp.web import Application

from rest_framework.authtoken.models import Token

from testapp.models import Message
from testapp.websockets import handler


@pytest.mark.django_db
def test_message_subscription(subscription):
    subscription.channel.name = "{0}:messages".format(subscription.subscriber.username)
    subscription.channel.save()
    message = mommy.make(Message, channel=subscription.channel, to_user=subscription.subscriber)

    loop = asyncio.get_event_loop()
    token, _ = Token.objects.get_or_create(user=subscription.subscriber)
    token = token.key

    @asyncio.coroutine
    def pub():
        yield from asyncio.sleep(1)
        message.publish()

    @asyncio.coroutine
    def start_server(loop):
        app = Application(loop=loop)
        app.router.add_route(*handler.route)
        routes = app.router.routes()._urls
        assert len(routes), routes
        srv = yield from loop.create_server(app.make_handler(), "localhost", 9000)
        return srv

    @asyncio.coroutine
    def go(loop):
        srv = yield from start_server(loop)
        uri = "http://localhost:9000?token=" + token
        client = yield from ws_connect(uri)
        yield from pub()
        message_ = yield from client.receive()
        assert message_.data == message.body

        yield from client.close()

        srv.close()
        yield from srv.wait_closed()

    loop.run_until_complete(go(loop))
