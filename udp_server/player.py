from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread
from twisted.internet.reactor import callLater as call_later

from apps.cache import (is_dirty, set_clean, remove_from_group, get_clients_from_group)
from apps.games.models import Game
from apps.players.serializers import PlayerMovedSerializer

from settings import RESPONSE_PLAYER_LEFT, RESPONSE_PLAYER_TRANSFORM


class Player:
    def __init__(self, protocol, player_state):
        self.disconnected = False
        self.protocol = protocol
        self.player_state = player_state

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
        if is_dirty(self.player_state.key):
            set_clean(self.player_state.key)
            yield defer_to_thread(self.player_state.refresh_from_db)
        else:
            try:
                self.player_state.game
            except Game.DoesNotExist:
                yield defer_to_thread(self.player_state.refresh_from_db)

    @inline_callbacks
    def on_disconnect(self):
        self.refresh_state()
        yield self.quit_game()
        self.disconnected = True

    @inline_callbacks
    def quit_game(self, _):
        if self.player_state.game:
            yield defer_to_thread(remove_from_group, self.player_state.game.key, self.player_state.address)
            self.protocol.queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data={
                    "player_id": self.player_state.key
                },
                address=self.player_state.address,
                group_name=self.player_state.game.key
            )
            yield defer_to_thread(self.player_state.quit_game)

    @inline_callbacks
    def move(self, message):
        for remote_address in self.remote_addresses_in_current_game:
            serializer = PlayerMovedSerializer(message)
            data = dict(serializer.data)
            data['key'] = self.player_state.key
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

        if self.player_state.game:
            addresses_in_current_game = yield defer_to_thread(get_clients_from_group, self.player_state.game.key)
            addresses_in_current_game.remove(self.player_state.address)
            self.remote_addresses_in_current_game = addresses_in_current_game

        call_later(1, self.update_remote_addresses_in_current_game)

    '''
    @inline_callbacks
    def move(self, message):
        if not self.player_state.game:
            return
        # serializer = ReceivePlayerInfoSerializer(message)
        serializer = PlayerMovedSerializer(message)

        for remote_client_id in self.remote_clients_from_current_game:
            yield defer_to_thread(
                add_message_to_broadcast,
                self.connection.key,
                remote_client_id,
                RESPONSE_PLAYER_TRANSFORM,
                self.state.snap_id + ',' + message
            )
    '''
