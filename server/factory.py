import logging
from autobahn.twisted.websocket import WebSocketServerFactory
from django.apps import apps
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import (add_message_to_broadcast_queue, add_to_group,
                        delete_group, flush_all, get_clients_from_group,
                        get_message_for_client, remove_from_group)

from environment import settings
from server.protocol import SocketProtocol

logger = logging.getLogger(__name__)


class GameServerFactory(WebSocketServerFactory):
    protocol = SocketProtocol

    def __init__(self, service):

        self.url = "ws://%s:%d" % (
            settings.WEBSOCKET_SERVER_HOST,
            settings.WEBSOCKET_SERVER_PORT
        )

        WebSocketServerFactory.__init__(
            self, self.url
        )
        # TODO: Remove
        self.reset_db()

        self.service = service
        self.name = 'factory'
        self.clients = []

    def buildProtocol(self, addr):
        return self.protocol(self, self.service)

    @inline_callbacks
    def add_to_group(self, group_name, client_id):
        yield defer_to_thread(add_to_group, group_name, client_id)

    @inline_callbacks
    def remove_group(self, group_name):
        yield defer_to_thread(delete_group, group_name)

    @inline_callbacks
    def unregister_from_group(self, group_name, client_key):
        yield defer_to_thread(remove_from_group, group_name, client_key)

    def register(self, client):
        if client not in self.clients:
            self.clients.append(client)
            logger.info("[%s] added %s - %s" % (self.name, client.ip, client.key))
            # self.broadcast(action='in', sender=client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)
            logger.info("[%s] removed %s - %s" % (self.name, client.ip, client.key))

        del client

    # ------------------------ Send
    @inline_callbacks
    def queue_to_broadcast(self, action, sender_id, data=None, exclude_sender=False, group_name=None):
        if not group_name:
            raise Exception("We need a group name to broadcast!")
        for client_id in get_clients_from_group(group_name):

            if exclude_sender and sender_id == client_id:
                continue
            yield defer_to_thread(add_message_to_broadcast_queue, client_id, action, data)

    def consume_queued_broadcast_messages(self):
        for client in self.clients:
            for action, data in get_message_for_client(client.key):
                client.send(action=action, data=data)

    def local_broadcast(self, action, sender_id, data=None, exclude_sender=True, group_name=None):
        if not group_name:
            raise Exception("We need a group name to broadcast!")
        group_clients = get_clients_from_group(group_name)
        for client in self.clients:
            if client.key in group_clients:
                if exclude_sender and sender_id == client.key:
                    continue
                client.send(action=action, data=data)

    def reset_db(self):
        Player = apps.get_model('players', 'Player')
        Game = apps.get_model('games', 'Game')
        for player in Player.objects.all():
            player.game = None
            player.save()
        Game.objects.all().delete()
        flush_all()
