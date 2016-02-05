from django.conf import settings
from django.db import models

from redis_pubsub.models import PublishableModel


class Message(PublishableModel):
    """
    """
    PUBLISH_ON_CREATE = True
    PUBLISH_ON_UPDATE = True

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL)

    body = models.TextField()
