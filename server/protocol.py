import json
import logging
import uuid

from autobahn.twisted.websocket import WebSocketServerProtocol
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread
from twisted.web import _responses as responses

from apps.cache import (add_logged_player, delete_player_to_client,
                        get_logged_players, remove_broadcast_queue,
                        set_player_to_client)

from apps.players.models import Player as PlayerState
from apps.players.serializers import (AuthSerializer, SendAuthSerializer)
from server.player import Player
from settings import RESPONSE_PLAYER_ALREADY_LOGGED, RESPONSE_AUTH_FAILURE, RESPONSE_AUTH_PLAYER


logger = logging.getLogger(__name__)


class SocketProtocol(WebSocketServerProtocol):
    player = None

    def __init__(self, factory, service):
        WebSocketServerProtocol.__init__(self)

        self.factory = factory
        self.service = service
        self.name = 'socket'
        self.user = None
        self.ip = None
        self.key = uuid.uuid4().hex

        self.actions = {
            "auth": self.auth
        }

    def onConnect(self, connection_request):
        try:
            self.ip = connection_request.headers['x-real-ip']
        except (AttributeError, KeyError):  # running without nginx
            self.ip = '127.0.0.1'
        logger.info('[%s] connected: %s' % (self.name, self.ip))

    def onOpen(self):
        self.factory.register(self)

    @inline_callbacks
    def onMessage(self, payload, is_binary):
        try:
            data = json.loads(payload.decode('utf8'))
        except ValueError:
            # could not parse upstream json
            self.send_error({'message': 'Invalid JSON.'})
            return

        if 'action' not in data:
            self.send_error({'message': 'Action needed.'})
            return

        action = data['action']
        data = data.get('data', {})
        sent = False

        logger.debug('<<<<<<<< Receivning ::: {}'.format(action))

        if action in self.actions:
            sent = True
            yield self.actions[action](data)

        if self.player and action in self.player.actions:
            sent = True
            yield self.player.execute_action(action, data)

        if action in self.service.actions:
            sent = True
            yield self.service.actions[action](self, data)

        if not sent:
            self.send_error("Action {} not allowed".format(action))

    def send(self, action, code=responses.OK, data=None, sender=None):
        logger.debug('>>>>>>>>>>>>>>>>> Sending ::: {}'.format(action))

        response = {'code': code, 'action': action}
        if data is not None:
            response['data'] = data
        if sender is not None:
            response['sender'] = sender.key

        self.sendMessage(json.dumps(response).encode('utf8'))

    def send_error(self, data=None):
        self.send(code=responses.BAD_REQUEST, action='error', data=data)

    @inline_callbacks
    def connectionLost(self, reason):
        if self.player:
            yield self.player.on_disconnect()
            yield defer_to_thread(delete_player_to_client, self.player.state.snap_id)

        yield defer_to_thread(remove_broadcast_queue, self.key)
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def sendServerStatus(self, redirectUrl=None, redirectAfter=0):
        """ Overriding Autobahns' default status page """
        self.send(code=responses.OK, action='status')

    def queue_to_broadcast(self, action, data=None, exclude_sender=True, group_name=None):
        self.factory.queue_to_broadcast(action, self, data, exclude_sender=exclude_sender, group_name=group_name)

    @inline_callbacks
    def auth(self, message):
        if self.player is not None:
            return

        serializer = AuthSerializer(data=message)
        if not serializer.is_valid():
            self.send_error(serializer.errors)
            return

        player_state, error = yield defer_to_thread(
            PlayerState.objects.auth,
            serializer.data['name']
        )
        if not player_state:
            self.send(RESPONSE_AUTH_FAILURE, data=error)
            return

        logged_players = yield defer_to_thread(get_logged_players)
        if player_state.key in logged_players:
            self.send(
                RESPONSE_PLAYER_ALREADY_LOGGED,
                data=serializer.data['name']
            )

        yield defer_to_thread(add_logged_player, player_state.key)
        yield defer_to_thread(set_player_to_client, player_state.key, self.key)

        self.player = Player(self, player_state)

        serializer = SendAuthSerializer(player_state)

        self.send(
            RESPONSE_AUTH_PLAYER,
            data=serializer.data
        )
        self.player.join_game()
