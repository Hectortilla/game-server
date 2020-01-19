import datetime
import logging

from django.db import connection
from django.db.utils import OperationalError
from twisted.application import service
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import get_game_players_data, list_games
from environment import settings
from apps.players.serializers import SendPlayerTransformSerializer
from settings import RESPONSE_PLAYERS_TRANSFORM

logger = logging.getLogger(__name__)


class GameServerService(service.Service):

    def __init__(self, game_protocol):
        self.protocol = game_protocol
        self.actions = {}

    def startService(self):
        logger.info('[%s] starting on port: %s' % (
            self.name, settings.SOCKET_SERVER_PORT
        ))

        '''self.listener = reactor.listenUDP(
            settings.SOCKET_SERVER_PORT, self.protocol
        )
        '''
        call_later(0, self.ping_db)
        call_later(0, self.send_position_update)
        call_later(0, self.consume_broadcast_messages)
        call_later(0, self.check_disconnect)

    def ping_db(self):
        try:
            connection.connection.ping()
        except (OperationalError, AttributeError):
            from django import db
            db.close_old_connections()
        call_later(settings.SERVER_DB_KEEPALIVE, self.ping_db)

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

    @inline_callbacks
    def consume_broadcast_messages(self):
        yield self.protocol.consume_queued_broadcast_messages()
        call_later(settings.BROADCAST_INTERVAL, self.consume_broadcast_messages)

    @inline_callbacks
    def check_disconnect(self):
        yield self.protocol.check_disconnect()
        call_later(1, self.check_disconnect)
