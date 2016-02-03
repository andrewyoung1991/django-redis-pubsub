from django.conf import settings


REDIS_PUBSUB = getattr(settings, "REDIS_PUBSUB", {})
REDIS_PUBSUB.setdefault("address", ("localhost", 6379))
REDIS_PUBSUB.setdefault("db", 0)
REDIS_PUBSUB.setdefault("password", None)
