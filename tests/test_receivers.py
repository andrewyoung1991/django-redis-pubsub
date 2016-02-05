import asyncio
from unittest import mock

import pytest

from testapp.models import Message


LOOP = asyncio.get_event_loop()


@pytest.mark.django_db
def test_post_save_signals(subscription):
    reader = subscription.get_reader()
    assert not reader.is_active
    m = mock.Mock()

    message = Message(
        to_user=subscription.subscriber,
        from_user=subscription.subscriber,
        body="hi!",
        channel=subscription.channel
        )

    expect = iter(["hi!", "oh sorry"])
    continue_ = iter([True, False])

    @asyncio.coroutine
    def saveit():
        yield from asyncio.sleep(1)
        message.save()

    @asyncio.coroutine
    def updateit():
        yield from asyncio.sleep(1)
        message.body = "oh sorry"
        message.save()

    @reader.callback
    def callback(channel_name, model):
        assert model.id == message.id
        assert model.body == next(expect)
        return next(continue_)

    @asyncio.coroutine
    def go():
        listener = yield from reader.listen()
        assert reader.is_active
        yield from saveit()
        yield from updateit()
        yield from listener

        assert not reader.is_active

        yield from reader.manager.stop()
        assert reader.manager.closed

    LOOP.run_until_complete(go())
