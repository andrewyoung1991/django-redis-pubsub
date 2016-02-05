from django.db.models import signals
from django.dispatch import receiver

from . import models


def subscribable_changed(sender, instance, created, **kwargs):
    """ handle publishing a new, or updated subscribable model.
    """
    if created:
        publish = sender.PUBLISH_ON_CREATE
    else:
        publish = sender.PUBLISH_ON_UPDATE

    if publish:  # pragma: no branch
        instance.publish()


for subklass in models.PublishableModel.__subclasses__():
    receiver(signals.post_save, sender=subklass)(subscribable_changed)
