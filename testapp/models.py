from django.conf import settings
from django.db import models

from redis_pubsub.models import PublishableModel


class Message(PublishableModel):
    """
    """
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL)

    body = models.TextField()
