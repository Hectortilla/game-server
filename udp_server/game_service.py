import datetime
import logging

from udp_server.game_instance import GameInstance
from django.db import connection
from django.db.utils import OperationalError
from twisted.application import service
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import get_game_players_data, list_games, add_game, add_player_to_game
from django.apps import apps

from environment import settings
from apps.players.serializers import SendPlayerTransformSerializer, GamePlayersSerializer, GameJoinedSerializer, \
    PlayerJoinedGameSerializer
from settings import RESPONSE_PLAYERS_TRANSFORM, RESPONSE_JOINED_GAME, RESPONSE_GAME_PLAYERS, RESPONSE_PLAYER_JOINED

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
        # call_later(0, self.send_position_update)

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
        game, created = yield defer_to_thread(Game.objects.get_or_create, seed=0)
        add_player_to_game(game.key, player.player_state.key)
        if created or not game.get_players():
            # add_game(game.key)
            self.game_instances[game.key] = GameInstance(self, self.protocol, game)

        player.player_state.game = game
        yield defer_to_thread(player.player_state.save)

    '''
    @inline_callbacks
    def send_position_update(self):
        games = yield defer_to_thread(list_games)
        for game_key in games:
            players_info = yield defer_to_thread(get_game_players_data, game_key)

            if players_info:
                self.protocol.single_message_to_broadcast(
                    RESPONSE_PLAYERS_TRANSFORM,
                    data={"transforms": players_info},
                    group_name=game_key
                )

        call_later(settings.SERVER_MAIN_LOOP_INTERVAL, self.send_position_update)
    '''

