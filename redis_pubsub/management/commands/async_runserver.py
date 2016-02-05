from django.core.management.base import BaseCommand
from django.core.wsgi import get_wsgi_application

from aiohttp_wsgi import WSGIHandler

from redis_pubsub.contrib import websockets


class Command(BaseCommand):
    """ an alternative to Djangos runserver command. simply runs the django wsgi
    application as an endpoint in a Aiohttp app. All requests to the wsgi endpoints are
    run in the event loop executor in the same event loop as your websocket coroutines.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            "--host", default="localhost",
            help="the hostname to serve on"
            )
        parser.add_argument(
            "--port", default=8000, type=int,
            help="the port to serve on"
            )

    def handle(self, *args, **options):
        host = options["host"]
        port = options["port"]

        print("Prepairing async server ...")
        loop = asyncio.get_event_loop()
        wsgi_app = WSGIHandler(get_wsgi_application(), loop=loop)
        aio_app = websockets.setup(loop=loop)
        aio_app.router.add_route("*", "/{path_info:.*}", wsgi_app.handle_request)

        print("Starting async server ...")
        server = loop.create_server(aio_app.make_handler(), host, port)
        server = loop.run_until_complete(server)
        try:
            print("Server running on {0}:{1}\n CTRL-C to stop.".format(host, port))
            loop.run_forever()
        except KeyboardInterrupt:
            print("Stopping server...")
