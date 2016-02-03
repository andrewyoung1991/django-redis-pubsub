import asyncio

from unittest import mock

import pytest

from redis_pubsub import models, util


LOOP = asyncio.get_event_loop()


@pytest.mark.django_db
def test_reader(subscription):
    reader = subscription.get_reader()
    assert not reader.is_active
    m = mock.Mock()

    @reader.callback
    def callback(channel_name, model):
        m(model)
        return False

    @asyncio.coroutine
    def go():
        listener = yield from reader.listen()
        assert reader.is_active
        listener.cancel()
        with pytest.raises(asyncio.CancelledError):
            yield from listener

        assert not reader.is_active
        assert not m.called

        yield from reader.manager.stop()
        assert reader.manager.closed

    LOOP.run_until_complete(go())


@pytest.mark.django_db
def test_publish_reader(subscription):
    reader = subscription.get_reader()
    publisher = subscription.subscriber

    m = mock.Mock()

    @reader.callback
    def callback(channel_name, model):
        m(model)
        return False

    @asyncio.coroutine
    def pub():
        return subscription.channel.publish(publisher)

    @asyncio.coroutine
    def go():
        listener = yield from reader.listen()
        assert reader.is_active

        yield from pub()
        yield from listener

        assert not reader.is_active
        m.assert_called_with(publisher)

        yield from reader.manager.stop()
        assert reader.manager.closed

    LOOP.run_until_complete(go())


@pytest.mark.django_db
def test_channel_subscription_returns_reader(subscription):
    reader = subscription.channel.subscribe(subscription.subscriber)
    assert isinstance(reader, util.ChannelReader)


@pytest.mark.django_db
def test_close_reader(subscription):
    reader = subscription.get_reader()
    publisher = subscription.subscriber

    m = mock.Mock()
    continue_ = iter([True, False])

    @reader.callback
    def callback(channel_name, model):
        m(model)
        return next(continue_)

    @asyncio.coroutine
    def pub():
        return subscription.channel.publish(publisher)

    @asyncio.coroutine
    def go():
        listener = yield from reader.listen()
        assert reader.is_active

        # publish 2 messages
        yield from pub()
        yield from pub()
        yield from listener

        assert not reader.is_active
        m.assert_called_with(publisher)

        yield from reader.manager.stop()
        assert reader.manager.closed

    LOOP.run_until_complete(go())


@pytest.mark.django_db
def test_close_manager(subscription):
    reader = subscription.get_reader()

    m = mock.Mock()

    @reader.callback
    def callback(channel_name, model):
        m(model)
        return next(continue_)

    @asyncio.coroutine
    def go():
        listener = yield from reader.listen()
        assert reader.is_active

        yield from reader.manager.remove(reader)

        with pytest.raises(asyncio.CancelledError):
            yield from listener

        assert not m.called

        yield from reader.manager.stop()
        assert reader.manager.closed

    LOOP.run_until_complete(go())
