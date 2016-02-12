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
        """ provides information on whether or not this channel is active, i.e. has
        active subscriptions. this property is used in the `publish` method to ensure no
        unnecessary publish actions are executed if there aren't any listeners.
        """
        return self.subscribers.filter(active=True).exists()

    def subscribe(self, subscriber):
        """ returns a Subscription instance.
        """
        model, _ = Subscription.objects.get_or_create(subscriber=subscriber, channel=self)
        model.active = True
        model.save()
        return model

    def publish(self, model):
        """ reduces the model into a json serializable dict that can be recovered by a
        subscriber coroutine.
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
    also be *turned off* by setting `.active = False`
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
    publishable model is published and sent to a subscriber. this model is mainly a
    utility method for debugging whether or not a PublishableModel was delivered. If,
    for instance, a model is published and there are no subscribers actively listening,
    then no ReceivedPublication will be created. A useful query, to catch users back up
    on their subscriptions is to find all the PublishableModels that publish on channels
    a user subscribes to and cross reference those with non-existing
    ReceivedPublications.

    .. code:: python

        message = Message.objects.first()
        subscribers = message.channel.subscribers.all()
        received = ReceivedPublication.objects.filter(
            publication=message, channel=message.channel, subscriber__in=subscribers
            )
        received_by = received.values_list("subscriber_id", flat=True)
        not_received_by = subscribers.exclude(id__in=received_by)
        # do something with the subscribers who have not received this message.

        # or, with the subscriber as the starting point
        subscriptions = subscriber.subscriptions.select_related("channel")
        channels = (s.channel for s in subscriptions)
        publications = []
        for channel in channels:
            if hasattr(channel, "publishable_messages"):
                messages = channel.publishable_messages.all()
                publications.extend(messages)
        received = ReceivedPublication.objects.filter(
            channel=channel, subscriber=subscriber, publication__in=publications
            ).values_list("publication_id", flat=True)
        not_received = Message.objects.exclude(id__in=received)

    it may be wise in your application to create an additional utility model that acts
    as a queue for undelivered publications.

    .. code:: python

        class QueuedPublication(models.Model):
            subscriber = models.ForeignKey(settings.AUTH_USER_MODEL,
                                            related_name="queued_publications")
            publication_type = models.ForeignKey(ContentType, null=True)
            publication_id = models.PositiveIntegerField(null=True)
            publication = GenericForeignKey("publication_type", "publication_id")

            @classmethod
            def find_all_undelivered(cls):
                queue = []
                for publishable in PublishableModel.__subclasses__():
                    for instance in publishable.objects\
                                            .select_related("channel")\
                                            .prefetch_related("channel__subscribers"):
                        channel = instance.channel
                        subscribers = channel.subscribers.all()
                        received = ReceivedPublication.objects.filter(
                            publication=instance, channel=message.channel,
                            subscriber__in=subscribers
                            ).values_list("subscriber_id", flat=True)
                        not_received_by = subscribers.exclude(id__in=received_by)
                        for subscriber in not_received_by:
                            queued = cls(subscriber=subscriber, publication=instance)
                            queue.append(queued)
                cls.objects.bulk_create(queue)

    the preceeding model could run its `find_all_undelivered` method in a cronjob, and
    perhaps, deliver all of the publications the next time the subscriber is connected.
    of course, this code would have to be cleaned up as it inherently allows for a
    massive amount of duplication.
    """
    channel = models.ForeignKey("Channel", related_name="publications")
    subscriber = models.ForeignKey(user_model, related_name="received_publications")
    datetime_received = models.DateTimeField(auto_now_add=True, editable=False)

    publication_type = models.ForeignKey(ContentType, null=True)
    publication_id = models.PositiveIntegerField(null=True)
    publication = GenericForeignKey("publication_type", "publication_id")
