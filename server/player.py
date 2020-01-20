from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import (get_clients_from_group, is_dirty, remove_from_group,
                        set_clean)
from apps.games.models import Game
from apps.players.serializers import PlayerMovedSerializer
from settings import RESPONSE_PLAYER_LEFT, RESPONSE_PLAYER_TRANSFORM
from utils import queue_to_broadcast


class Player:
    def __init__(self, protocol, state):
        self.disconnected = False
        self.protocol = protocol
        self.state = state

        self.remote_addresses_in_current_game = []
        call_later(1, self.update_remote_addresses_in_current_game)

        self.actions = {
            "move": self.move,
        }

    @inline_callbacks
    def execute_action(self, action, data):
        yield self.refresh_state()
        yield self.actions[action](data)

    @inline_callbacks
    def refresh_state(self):
        if is_dirty(self.state.key):
            set_clean(self.state.key)
            yield defer_to_thread(self.state.refresh_from_db)
        else:
            try:
                self.state.game
            except Game.DoesNotExist:
                yield defer_to_thread(self.state.refresh_from_db)

    @inline_callbacks
    def on_disconnect(self):
        self.refresh_state()
        yield self.quit_game(None)
        self.disconnected = True

    @inline_callbacks
    def quit_game(self, _):
        if self.state.game:
            yield defer_to_thread(remove_from_group, self.state.game.key, self.state.address)
            queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data={
                    "player_id": self.state.key
                },
                address=self.state.address,
                group_name=self.state.game.key
            )
            yield defer_to_thread(self.state.quit_game)

    @inline_callbacks
    def move(self, message):
        for remote_address in self.remote_addresses_in_current_game:
            serializer = PlayerMovedSerializer(message)
            data = dict(serializer.data)
            data['key'] = self.state.key
            self.protocol.send(
                remote_address,
                RESPONSE_PLAYER_TRANSFORM,
                data
            )
        yield

    @inline_callbacks
    def update_remote_addresses_in_current_game(self):
        if self.disconnected:
            return

        if self.state.game:
            addresses_in_current_game = yield defer_to_thread(get_clients_from_group, self.state.game.key)
            addresses_in_current_game.remove(self.state.address)
            self.remote_addresses_in_current_game = addresses_in_current_game

        call_later(1, self.update_remote_addresses_in_current_game)
