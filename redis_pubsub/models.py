from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core import serializers
from django.db import models

from . import util

user_model = settings.AUTH_USER_MODEL

__all__ = (
    "PublishableModel", "Channel", "Subscription", "ReceivedPublication"
    )


class PublishableModel(models.Model):
    """ an abstract base model for publishable models. Models are published to channels
    using redis pub sub methods.

    A publishable model is published on its related channel. A channel must be created
    for the publishable model before saving. The channel does not need to be unique for
    for the publisher.
    """
    PUBLISH_ON_CREATE = False
    PUBLISH_ON_UPDATE = False

    channel = models.ForeignKey("Channel", related_name="publishable_%(class)ss")

    class Meta:
        abstract = True

    def subscribe(self, *subscribers):  # pragma: no cover
        """ Create a subscription to this models channel for each of the `subscribers`
        """
        for subscriber in subscribers:
            self.channel.subscribe(subscriber)

    def publish(self):  # pragma: no cover
        """ publish this model on its channel
        """
        self.channel.publish(self)

    def serialize(self):  # pragma: no cover
        """ a generic serialization method for all publishable models
        """
        return serializers.serialize("json", [self])


class Channel(models.Model):
    """ A channel is unaware of the publisher or the subscriber, it is simply a uniquely
    named object with which clients can subscribe to publications through. A single
    channel may be used to publish many models to many subscribers, because of this
    any subscription handler method should be prepared to handle any of the possible
    models sent through the channel.
    """
    name = models.CharField(max_length=100, unique=True)
    datetime_created = models.DateTimeField(auto_now_add=True)

    @property
    def active(self):
        return self.subscribers.filter(active=True).exists()

    def subscribe(self, subscriber):
        """ returns an unmanaged ChannelReader object
        """
        model, _ = Subscription.objects\
                    .get_or_create(subscriber=subscriber, channel=self)
        return model

    def publish(self, model):
        """
        """
        if self.active:  # pragma: no branch
            klass = type(model)
            # make this model json serializable / recoverable
            kwargs = {
                "app_label": klass._meta.app_label,
                "object_name": klass._meta.object_name,
                "pk": model.pk
                }
            util.redis_channel_publish(self.name, kwargs)


class Subscription(models.Model):
    """ A subscriber can have many subscriptions to unique channels. a subscription may
    also be `turned off` by setting `.active = False`
    """
    subscriber = models.ForeignKey(user_model, related_name="subscriptions")
    channel = models.ForeignKey("Channel", related_name="subscribers")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("subscriber", "channel")

    def get_reader(self, manager=None):
        """ returns a wrapper that takes a callback as its argument. this callback will
        be passed the `id` of the published model, so the callback must be aware of the
        model class that it is subscribed to through a channel.

        .. code:: python

            @asyncio.coroutine
            def subscription(channel_name):
                s = Subscription.objects.get(subscriber_id=1, channel__name=channel_name)
                channel_reader = s.get_reader()

                @channel_reader.callback
                def message_sender(message):
                    serialized = MessageSerializer(message).data
                    websocket.send_str(serialized)
                    return True

                yield from message_sender.listen()
        """
        return util.ChannelReader(self, manager=manager)


class ReceivedPublication(models.Model):
    """ a utility model for tracking the delivery status of a publication. Whenever a
    publishable model is published and sent to a subscriber.
    """
    channel = models.ForeignKey("Channel", related_name="publications")
    subscriber = models.ForeignKey(user_model, related_name="received_publications")
    datetime_received = models.DateTimeField(auto_now_add=True, editable=False)

    publication_type = models.ForeignKey(ContentType, null=True)
    publication_id = models.PositiveIntegerField(null=True)
    publication = GenericForeignKey("publication_type", "publication_id")
