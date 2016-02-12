default_app_config = "redis_pubsub.apps.RedisPubsubConfig"

from django.conf import settings


REDIS_PUBSUB = getattr(settings, "REDIS_PUBSUB", {})
REDIS_PUBSUB.setdefault("address", ("localhost", 6379))
REDIS_PUBSUB.setdefault("db", 0)
REDIS_PUBSUB.setdefault("password", None)
REDIS_PUBSUB.setdefault("tokenauth_method", "redis_pubsub.auth.authtoken_method")
REDIS_PUBSUB.setdefault("websocket_url_prefix", "")
REDIS_PUBSUB.setdefault("append_slash", settings.APPEND_SLASH)


def get_application(loop=None):
    """ get websockets and wsgi application as a single Aiohttp application object.
    """
    from aiohttp_wsgi import WSGIHandler
    from redis_pubsub.contrib import websockets
    wsgi_app = WSGIHandler(get_wsgi_application(), loop=loop)
    aio_app = websockets.setup(loop=loop)
    aio_app.router.add_route("*", "/{path_info:.*}", wsgi_app.handle_request)
    return aio_app
