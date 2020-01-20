import logging

from django.apps import apps
from twisted.application import service
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import get_clients_from_group
from apps.players.serializers import (GameJoinedSerializer,
                                      GamePlayersSerializer,
                                      PlayerJoinedGameSerializer, PlayerLeftGameSerializer)
from settings.constants import (RESPONSE_GAME_PLAYERS, RESPONSE_JOINED_GAME,
                                RESPONSE_PLAYER_JOINED, RESPONSE_PLAYER_LEFT)
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
        self.addresses = set()

        addresses = yield defer_to_thread(get_clients_from_group, self.state.key)
        for address in addresses:
            yield self.add_address(address)

        call_later(0, self.check_players)

    @inline_callbacks
    def add_address(self, address):
        Player = apps.get_model('players', 'Player')

        self.addresses.add(address)

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
    def remove_address(self, address):
        Player = apps.get_model('players', 'Player')

        self.addresses.remove(address)
        player = yield Player.objects.get(address=address)

        queue_to_broadcast(
            RESPONSE_PLAYER_LEFT,
            exclude_sender=True,
            data=PlayerLeftGameSerializer(player).data,
            address=address,
            group_name=self.state.key
        )

    @inline_callbacks
    def check_players(self):
        if not self.addresses:
            self.stopService()
            return

        addresses = yield defer_to_thread(get_clients_from_group, self.state.key)
        addresses = set(addresses)

        new_players = addresses - self.addresses
        gone_players = self.addresses - addresses

        for address in new_players:
            yield self.add_address(address)
        for address in gone_players:
            yield self.remove_address(address)
        call_later(1, self.check_players)
