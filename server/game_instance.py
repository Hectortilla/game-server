import logging

from django.apps import apps
from twisted.application import service
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import get_clients_from_group
from apps.players.serializers import (GameJoinedSerializer,
                                      GamePlayersSerializer,
                                      PlayerJoinedGameSerializer)
from settings.constants import (RESPONSE_GAME_PLAYERS, RESPONSE_JOINED_GAME,
                                RESPONSE_PLAYER_JOINED)
from utils import queue_to_broadcast

logger = logging.getLogger()

position_update_interval = 0


class GameInstance(service.Service):

    def __init__(self, service, protocol, state):
        self.finished = False
        self.service = service
        self.protocol = protocol

        self.state = state
        self.key = self.state.key
        self.addresses = []

        call_later(0, self.check_for_new_players)

    @inline_callbacks
    def add_address(self, address):
        Player = apps.get_model('players', 'Player')

        self.addresses.append(address)

        data = {
            "players": GamePlayersSerializer(self.state.get_players(), many=True).data
        }
        self.protocol.send(address, RESPONSE_JOINED_GAME, data=GameJoinedSerializer(self.state).data)
        self.protocol.send(address, RESPONSE_GAME_PLAYERS, data=data)

        player = yield Player.objects.get(address=address)
        queue_to_broadcast(
            RESPONSE_PLAYER_JOINED,
            exclude_sender=True,
            data=PlayerJoinedGameSerializer(player).data,
            address=address,
            group_name=self.state.key
        )

    @inline_callbacks
    def check_for_new_players(self):
        addresses = yield defer_to_thread(get_clients_from_group, self.state.key)
        for address in addresses:
            if address not in self.addresses:
                yield self.add_address(address)
        call_later(1, self.check_for_new_players)
