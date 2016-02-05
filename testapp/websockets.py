import asyncio

from redis_pubsub.contrib.websockets import websocket_pubsub

@websocket_pubsub("/", authenticate=True)
def handler(ws, params, **kwargs):
    user = kwargs["user"]
    manager = kwargs["manager"]

    channel = "{0}:messages".format(user.username)
    reader = user.subscriptions.get(channel__name=channel).get_reader(manager)

    @reader.callback
    def send_message(channel_name, message):
        ws.send_str(message.body)
        return False

    listener = yield from reader.listen()
    yield from asyncio.gather(listener)


handlersconf = ["handler"]
