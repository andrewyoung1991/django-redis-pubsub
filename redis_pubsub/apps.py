from django.apps import AppConfig


class RedisPubsubConfig(AppConfig):
    name = "redis_pubsub"
    verbose_name = "PubSub Models"

    def ready(self):
        super(RedisPubsubConfig, self).ready()
        # connect all receivers
        from . import receivers
