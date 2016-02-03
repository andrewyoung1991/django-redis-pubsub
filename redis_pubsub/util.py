import functools as ft
import asyncio
import json

try:
    from django.db.models.loading import get_model
except ImportError:
    from django.apps import apps
    get_model = apps.get_model

import redis
import aioredis

from . import REDIS_PUBSUB


global SYNCREDIS, ASYNCREDIS
SYNCREDIS = None
ASYNCREDIS = None


def get_redis():
    """ initialize a syncronous redis connection
    """
    global SYNCREDIS
    if SYNCREDIS is None:  # pragma: no branch
        host, port = REDIS_PUBSUB["address"]
        db = REDIS_PUBSUB["db"]
        password = REDIS_PUBSUB["password"]
        SYNCREDIS = redis.Redis(host, port, db=db, password=password)
    return SYNCREDIS


@asyncio.coroutine
def get_async_redis():
    """ initialize an asyncronous redis connection
    """
    global ASYNCREDIS
    if ASYNCREDIS is None or ASYNCREDIS.closed:  # pragma: no branch
        address = REDIS_PUBSUB["address"]
        db = REDIS_PUBSUB["db"]
        password = REDIS_PUBSUB["password"]
        ASYNCREDIS = yield from aioredis.create_redis(address, db=db, password=password)
    return ASYNCREDIS


@asyncio.coroutine
def redis_channel_reader(channel, callback):
    """
    :param channel: the subscription channel to wait for messages on.
    :type channel: aioredis.Channel
    :param callback: a coroutine to await when a message is received
    :type callback: coroutine
    """
    while (yield from channel.wait_message()):
        message = yield from channel.get_json()
        continue_ = yield from callback(channel.name, message)
        if not continue_:
            channel.close()


def redis_channel_publish(channel, message):
    """
    :param channel: the channel description of the channel to publish a message on
    :type channel: str
    :param message: a json serializable message to send to the subscribed client
    :type message: dict
    """
    redis = get_redis()
    message = json.dumps(message)
    return redis.publish(channel, message)


class ChannelReader:
    """ a redis subscription channel reader

    .. code:: python

        subscription = account.subscriptions.get(channel__name="username:correspondence")

        @ChannelReader(subscription)
        def message_reader(channel, message):
            pass

        correspondence_reader.set_model(Message)

        future = yield from correspondence_reader.listen()
    """
    def __init__(self, subscription, manager=None):
        self.subscriber = subscription.subscriber
        self.channel = subscription.channel
        self._callback = None
        self.manager = manager
        self.future = None

    def __call__(self, callback):
        """ A callback takes a single argument of the model it will act upon, this model
        type is set with the `.set_model` method.

        .. code:: python

            subscription = user.subcriptions.first()
            reader = ChannelReader(subscription)
            reader.set_model(Message)

            @reader.callback
            def callback(message):
                # .. does stuff with the message
                return True
        """
        from .models import ReceivedPublication
        callback = asyncio.coroutine(callback)

        @ft.wraps(callback)
        @asyncio.coroutine
        def wrapper(channel_name, kwargs):
            publication = self.get_model_instance(**kwargs)
            continue_ = yield from callback(channel_name, publication)

            ReceivedPublication.objects.create(
                channel=self.channel,
                subscriber=self.subscriber,
                publication=publication
                )
            return continue_

        self._callback = wrapper

        return self

    callback = __call__

    @property
    def is_active(self):
        if self.future is not None:
            return not self.future.done()
        return False

    @staticmethod
    def get_model_instance(app_label, object_name, pk):
        klass = get_model(app_label, object_name)
        return klass.objects.get(pk=pk)

    @asyncio.coroutine
    def listen(self):
        """ a coroutine object that listens to the pubsub channel and calls. this returns
        a cancellable Future that, with a manager, can be cancelled before it is awaited.

        ::

            yield from reader.listen()
            reader.is_active  # True
        """
        yield from self.get_manager()
        channel = (yield from self.manager.redis.subscribe(self.channel.name))[0]
        self.future = asyncio.ensure_future(redis_channel_reader(channel, self._callback))
        return self.future

    @asyncio.coroutine
    def get_manager(self):
        if self.manager is None:  # pragma: no branch
            redis_ = yield from get_async_redis()
            self.manager = SubscriptionManager(redis_)
        self.manager.add(self)
        return self.manager


class SubscriptionManager:
    """ A proxy class in front of the aioredis object.
    """
    def __init__(self, redis_):
        self.readers = {}
        self.redis = redis_

    def add(self, *readers):
        for reader in readers:
            self.readers[reader.channel.name] = reader

    @property
    def closed(self):
        return self.redis.closed

    @asyncio.coroutine
    def remove(self, reader):
        if reader.is_active:
            reader.future.cancel()
        yield from self.redis.unsubscribe(reader.channel.name)
        self.readers.pop(reader.channel.name, None)

    @asyncio.coroutine
    def clear(self):
        coroutines = [self.remove(reader) for reader in self.readers.values()]
        yield from asyncio.gather(*coroutines)

    @asyncio.coroutine
    def stop(self):
        yield from self.clear()
        self.redis.close()
        yield from self.redis.wait_closed()
