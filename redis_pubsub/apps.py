from django.apps import AppConfig


class RedisPubsubConfig(AppConfig):
    name = "redis_pubsub"
    verbose_name = "Redis PubSub"

    def ready(self):
        super(RedisPubsubConfig, self).ready()
        # connect all receivers
        from . import receivers
