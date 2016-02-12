===================
Django Redis PubSub
===================

.. image:: https://travis-ci.org/andrewyoung1991/django-redis-pubsub.svg?branch=master
    :target: https://travis-ci.org/andrewyoung1991/django-redis-pubsub

.. image:: https://coveralls.io/repos/github/andrewyoung1991/django-redis-pubsub/badge.svg?branch=master
    :target: https://coveralls.io/github/andrewyoung1991/django-redis-pubsub?branch=master

.. image:: https://codeclimate.com/github/andrewyoung1991/django-redis-pubsub/badges/gpa.svg
    :target: https://codeclimate.com/github/andrewyoung1991/django-redis-pubsub
    :alt: Code Climate


asyncronous subscription distrobution for django (with websocket support!!!!).


PublishableModel
================

You'll first need to create some publishable models.

.. code:: python

    # models.py

    class Correspondence(PublishableModel):
        PUBLISH_ON_CREATE = False
        PUBLISH_ON_UPDATE = False

        participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="correspondences")

        def save(self, *args, **kwargs):
            super(Correspondence, self).save(*args, **kwargs)
            # add subscribe all the users to the channel
            channel = self.channel
            for subscriber in self.participants:
                channel.subscribe(subscriber)


    class Message(PublishableModel):
        PUBLISH_ON_CREATE = True
        PUBLISH_ON_UPDATE = False

        correspondence = models.ForeignKey("Correspondence", related_name="messages")
        author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_messages")
        body = models.TextField()

        def save(self, *args, **kwargs):
            if not hasattr(self, "channel"):
                self.channel = self.correspondence.channel
            super(Message, self).save(*args, **kwargs)

    # views.py

    def send_message(request, correspondence, *args, **kwargs):
        message = Message.objects.create(
            correspondence_id=correspondence,
            author=request.user,
            body=request.POST["body"]
        return render_to_response(request, "messages.html", {"message": message})

    # websockets.py

    @websocket_pubsub(authenticate=True)
    def read_messages(ws, params, user, manager):
        subscription = user.subscriptions.get(channel__name="something:unique".format(user.username))
        reader = subscription.get_reader(manager=manager)

        @reader.callback
        def send_message_alert(channel_name, model):
            alert = json.dumps({"message": "new message from {0}".format(model.author.get_full_name()))
            ws.send_str(alert)
            return True

        listener = yield from reader.listen()
        yield from listener


In the above example, a client who has established a websocket connection to the handler in `websockets.py` will receive alerts as long as the websocket connection remains open. When another client sends a POST request to the send_message view in `views.py` the message will be published and received by the `read_messages.send_message_alert` callback where further processing/serialization can occur.


Websockets
==========

If you choose to use `redis_pubsub.contrib.websockets` there are additional packages that you will need to install::

  $ pip install aiohttp aiohttp_wsgi

Websocket handlers belong in module in your application by the name of `websockets.py`. This module should export a `handlerconf`, which is a list of the names of the handlers in the module

.. code:: python

  @websocket("/")  # this handler will be at http://yourapp.com/
  def myhandler(ws, params, **kwargs):
      ...

  handlerconf = ["myhandler", ]

Websocket requests are handled with the excellent `aiohttp` package which takes care of the encoding/decoding, handshake, and cleanup of a websocket session. Handlers for websocket requests are coroutines decorated with either the `redis_pubsub.contrib.websockets.websocket` or `redis_pubsub.contrib.websockets.websocket_pubsub` wrappers. These wrappers handle converting your handler to a coroutine and passing arguments to your handler. A simple handler that echo's a message back to the client would look like this

.. code:: python

  @websocket("/echo")
  def echo(ws, params, **kwargs):
      message = yield from ws.receive()
      ws.send_str(message.data)

The former example shows a websocket handler that waits for a message from a connected client, echo's the message back to the client and closes the connection.


Websocket Authentication
========================

If you choose to use authenticated websockets you will need to either install `djangorestframework` and use the `rest_framework.authtoken.models.Token` object as your authentication method or simply use `rest_framework_jwt` to distribute and challenge JTW's provided by your client. to configure authentication with one of these methods (or your own token authentication method) add the module path to the REDIS_PUBSUB config::

  REDIS_PUBSUB = {
      "tokenauth_method": "redis_pubsub.auth.authjwt_method",  # defaults to "redis_pubsub.auth.authtoken_method"
  }

If you do decide to roll your own `tokenauth_method`, this method must accept a single argument (the token string) and return either `None` if the token is not valid or an instance of `AUTH_USER_MODEL` if the token is valid.


Websocket Pubsub
================

You can access the Pubsub methods provided by `redis_pubsub` in your websocket handlers by decorating your handler with the `redis.pubsub.contrib.websockets.websocket_pubsub` wrapper. This wrapper provides an additional argument `manager` to your handler. The manager can be used to keep track of subscription channels and stop them if necessary

.. code:: python

  # websockets.py

  @websocket_pubsub("/messages", authenticate=True)
  def message_pusher(ws, params, manager, user, **kwargs):
      subscription = user.subscriptions.get(channel__name="messages")
      reader = subscription.get_reader(manager=manager)

      @reader.callback
      def callback(channel_name, message):
          to_client = {
              channel_name: {
                  "author": message.author.username,
                  "body": message.body
              }
          }
          ws.send_str(json.dumps())
          return True

      listener = yield from reader.listen()
      yield from listener

This example shows the main purpose of the `redis_pubsub` package, which is to listen for updates on a redis channel and push the publication to a client. Lets break it down line by line

1) retreive the users subscription
2) create a managed ChannelReader object for this subscription
3) register a callback to be executed whenever a new publication is received
4) begin listening for changes
5) listen until the channel is closed

The most fruitful method offerd by a SubscriptionManager is `listen_to_all_subscriptions` which takes two arguments, a subscriber and a callback, and publishes subscriptions as they arrive

.. code:: python

  # websockets.py

  @websocket_pubsub("/subscriptions", authenticate=True)
  def subscriptions(ws, params, manager, user, **kwargs):

      def callback(channel_name, message):
          ws.send_str(message.serialize())
          return True

      manager.listen_to_all_subscriptions(user, callback)

      while True:
          message = yield from ws.receive()
          if message.tp not in (MsgType.error, MsgType.close):
              message = json.loads(message)
              if message["action"] == "unsubscribe":
                  subscription = user.subscriptions.get(channel__name=message["channe"])
                  subscription.active = False
                  subscription.save()
                  reader = manager.readers[message["channel"]]
                  yield from manager.remove(reader)
              elif message["action"] == "subscribe":
                  channel = Channel.objects.get(name=message["channel"])
                  reader = channel.subscribe(user).get_reader(manager=manager)
                  reader.callback(callback)
                  yield from reader.listen()
          else:
              break

The callback in this example will keep all subscription channels open and push messages to a client until the websocket has closed. This code provides a simple means of managing users with a multitude of subscriptions. The `while` loop here also handles unsubscribing and subscribing to new channels

.. note::

  A callback function should never receive from a websocket or else a RuntimeError will be raised.


Deploying
=========

when deploying an application with websockets/aiohttp you will not be able to use the normal django deployment proceedures. Since your django application will be a component of an AioHttp application object, you will have to use Gunicorn as an application server. Using utilities from the `redis_pubsub.contrib.websockets` module you can create a deployment file simply

.. code:: python

  # deployment.py

  import asyncio

  from django.core.wsgi import get_wsgi_application
  
  from aiohttp_wsgi import WSGIHandler
  
  from redis_pubsub.contrib.websockets import setup


  wsgi_app = get_wsgi_application()  # django.setup() is called here
  wsgi_handler = WSGIHandler(wsgi_app)
  
  loop = asyncio.get_event_loop()
  application = setup(loop=loop)
  # any url patterns not matched by the Websocket app go to the django app for handling
  application.router.add_route("*", "/{path_info:.*}", wsgi_handler.handle_request)

you can then start gunicorn by running::

  $ gunicorn deployment:application --bind localhost:8080 --worker-class aiohttp.worker.GunicornWebWorker
