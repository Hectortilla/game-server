import logging

from django.apps import apps
from django.db import connection
from django.db.utils import OperationalError
from server.protocol import GameProtocol
from twisted.application import service
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import add_to_group
from environment import settings
from server.game_instance import GameInstance

logger = logging.getLogger(__name__)


class GameService(service.Service):
    protocol = None

    def __init__(self):
        self.actions = {}

        self.game_protocol = GameProtocol(self)
        self.udp_service = None

    def startService(self):
        logger.info('[%s] starting on port: %s' % (
            self.name, settings.SOCKET_SERVER_PORT
        ))

        self.udp_service = reactor.listenUDP(settings.SOCKET_SERVER_PORT, self.game_protocol)

        call_later(0, self.ping_db)

    def ping_db(self):
        try:
            connection.connection.ping()
        except (OperationalError, AttributeError):
            from django import db
            db.close_old_connections()
        call_later(settings.SERVER_DB_KEEPALIVE, self.ping_db)

    @inline_callbacks
    def matchmake(self, player):
        Game = apps.get_model('games', 'Game')
        game, _ = yield defer_to_thread(Game.objects.get_or_create, seed=0)

        yield defer_to_thread(add_to_group, game.key, player.state.address)
        if not game.get_players():
            # self.game_instances[game.key] = yield GameInstance(self, self.protocol, game, player.state.address)
            game_instance = GameInstance(self.game_protocol, game)
            game_instance.setServiceParent(self.parent)

        player.state.game = game
        yield defer_to_thread(player.state.save)
