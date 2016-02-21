from django.contrib.contenttypes.models import ContentType
from django.db.models import manager


class PublishableModelManager(manager.Manager):
    def get_undelivered(self):
        """ a method that returns tuples of all instances of self.model that have not
        been delivered to a client. the tuples consist of a subscriber, instance pair.
        """
        from . models import ReceivedPublication

        undelivered = []
        for instance in self.get_queryset().iterator():
            subscriptions = instance.channel.subscribers.select_related("subscriber")
            ct = ContentType.objects.get_for_model(instance)
            id = instance.id
            subscribers = (s.subscriber for s in subscriptions)
            received = ReceivedPublication.objects.filter(
                                        publication_type=ct,
                                        publication_id=id,
                                        channel=instance.channel,
                                        subscriber__in=subscribers)
            recieved_by = received.values_list("subscriber_id", flat=True)
            for subscription in subscriptions.exclude(subscriber_id__in=recieved_by)\
                                .select_related("subscriber"):
                undelivered.append((subscription.subscriber, instance))

        return undelivered
