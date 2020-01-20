import datetime
import logging

from server.game_instance import GameInstance
from django.db import connection
from django.db.utils import OperationalError
from twisted.application import service

from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import add_to_group
from django.apps import apps

from environment import settings
logger = logging.getLogger(__name__)


class GameService(service.Service):
    protocol = None

    def __init__(self):
        # getServiceNamed
        # self.protocol = game_protocol
        self.actions = {}
        self.game_instances = {}

    def startService(self):
        logger.info('[%s] starting on port: %s' % (
            self.name, settings.SOCKET_SERVER_PORT
        ))

        '''self.listener = reactor.listenUDP(
            settings.SOCKET_SERVER_PORT, self.protocol
        )
        '''
        self.protocol = self.parent.getServiceNamed(settings.SERVER_NAME + '-udp-service').args[1]  # TODO: TEMP
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

        if not game.get_players():
            self.game_instances[game.key] = GameInstance(self, self.protocol, game)
        add_to_group(game.key, player.player_state.address)
        player.player_state.game = game
        yield defer_to_thread(player.player_state.save)
