from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import (is_dirty,
                        remove_logged_player, set_clean,
                        update_player_game_data_cache, add_player_to_game)
from apps.games.models import Game
from apps.players.serializers import (
    PlayerTransformSerializer, PlayerMovedSerializer, PlayerJoinedGameSerializer, GamePlayersSerializer,
    PlayerLeftGameSerializer, GameJoinedSerializer
)

from settings import RESPONSE_PLAYER_LEFT, RESPONSE_GAME_PLAYERS, RESPONSE_PLAYER_JOINED, RESPONSE_JOINED_GAME


class Player:
    def __init__(self, protocol, player_state, address):
        self.address = address
        self.address_key = address[0] + ':' + str(address[1])
        self.protocol = protocol
        self.player_state = player_state

        self.pk = player_state.pk

        self.actions = {
            # "positionUpdate": self.position_update,
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
    def _disconnect_from_game(self):
        if self.player_state.game:
            yield self.protocol.unregister_from_group(self.player_state.game.key, self.address_key)
            self.protocol.queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data=PlayerLeftGameSerializer(self.player_state).data,
                address_key=self.address_key,
                group_name=self.player_state.game.key
            )

            yield defer_to_thread(self.player_state.quit_game)

    @inline_callbacks
    def on_disconnect(self):
        self.refresh_state()
        yield self._disconnect_from_game()

        yield defer_to_thread(remove_logged_player, self.player_state.key)

    @inline_callbacks
    def position_update(self, message):
        if self.player_state.game:
            serializer = PlayerTransformSerializer({'key': self.player_state.key, **message})
            yield defer_to_thread(
                update_player_game_data_cache,
                self.player_state.key,
                self.player_state.game.key,
                serializer.data
            )

    @inline_callbacks
    def quit_game(self, _):
        if self.player_state.game:
            yield self.protocol.unregister_from_group(self.player_state.game.key, self.address_key)
            self.protocol.queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data={
                    "player_id": self.player_state.key
                },
                address_key=self.address_key,
                group_name=self.player_state.game.key
            )
            yield defer_to_thread(self.player_state.quit_game)

    @inline_callbacks
    def move(self, message):
        if self.player_state.game:
            serializer = PlayerMovedSerializer(message)
            data = dict(serializer.data)
            data['key'] = self.player_state.key
            yield defer_to_thread(
                update_player_game_data_cache,
                self.player_state.game.key,
                self.player_state.key,
                data
            )
    '''
    @inline_callbacks
    def move(self, message):
        if not self.player_state.game:
            return
        # serializer = ReceivePlayerInfoSerializer(message)
        serializer = PlayerMovedSerializer(message)

        self.protocol
        for remote_client_id in self.remote_clients_from_current_game:
            yield defer_to_thread(
                add_message_to_broadcast,
                self.connection.key,
                remote_client_id,
                RESPONSE_PLAYER_UPDATE,
                self.state.snap_id + ',' + message
            )
    '''