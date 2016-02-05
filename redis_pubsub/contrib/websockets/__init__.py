import asyncio

from django.conf import settings
from django.utils.module_loading import import_string

from aiohttp.web import Application

from .util import websocket, websocket_pubsub

__all__ = (
    "websocket", "websocket_pubsub", "setup"
    )


def load_handlers():
    """
    """
    handlers = []
    for app_ in settings.INSTALLED_APPS:
        try:
            module_path = ".".join([app_, "websockets"])
            handlers_ = import_string(".".join([module_path, "handlersconf"]))
            handlers_ = map(lambda x: ".".join([module_path, x]), handlers_)
            handlers.extend(handlers_)
        except (ImportError, AttributeError):
            pass
    return handlers


def setup(loop=None):
    """ use setup to dynamically build your Aiohttp websocket application
    """
    loop = asyncio.get_event_loop() if not loop else loop
    app = Application(loop=loop)
    handlers = load_handlers()
    for handler in handlers:
        handler = import_string(handler)
        app.router.add_route(*handler.route)
    return app
