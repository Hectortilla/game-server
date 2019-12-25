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
from udp_server.protocol import SocketProtocol
from apps.players.serializers import SendPlayerTransformSerializer
from settings import RESPONSE_PLAYERS_TRANSFORM

logger = logging.getLogger(__name__)


class GameServerService(service.Service):

    def __init__(self):
        self.protocol = SocketProtocol(self)
        self.tick = 0
        self.actions = {}

    def startService(self):
        # self.factory.startFactory()

        logger.info('[%s] starting on port: %s' % (
            self.name, settings.SOCKET_SERVER_PORT
        ))

        self.listener = reactor.listenUDP(
            settings.SOCKET_SERVER_PORT, self.protocol
        )

        call_later(0, self.ping_db)
        call_later(0, self.send_position_update)
        call_later(0, self.consume_broadcast_messages)

    def clock(self):
        self.tick += 1
        logger.debug("Clock: {}".format(datetime.datetime.now().strftime("%H:%M:%S.%f")))
        call_later(1, self.clock)

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
                self.protocol.local_broadcast(
                    RESPONSE_PLAYERS_TRANSFORM,
                    None,
                    data={"transforms": players_info},
                    group_name=game_key
                )

        call_later(settings.SERVER_MAIN_LOOP_INTERVAL, self.send_position_update)

    @inline_callbacks
    def consume_broadcast_messages(self):
        yield defer_to_thread(self.protocol.consume_queued_broadcast_messages)
        call_later(settings.BROADCAST_INTERVAL, self.consume_broadcast_messages)
