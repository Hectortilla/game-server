from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import (is_dirty,
                        remove_logged_player, set_clean,
                        update_player_game_data_cache)

from apps.games.models import Game
from apps.players.serializers import PlayerTransformSerializer

from settings import RESPONSE_PLAYER_LEFT


class Player:
    def __init__(self, connection, player_state):
        self.connection = connection
        self.player_state = player_state

        self.pk = player_state.pk

        self.actions = {
            "positionUpdate": self.position_update
        }

    def join_game(self):
        pass  # TODO

    @inline_callbacks
    def execute_action(self, action, data):
        yield self.refresh_state()
        yield self.actions[action](data)

    @inline_callbacks
    def refresh_state(self):
        if is_dirty(self.player_state.snap_id):
            set_clean(self.player_state.snap_id)
            yield defer_to_thread(self.player_state.refresh_from_db)
        else:
            try:
                self.player_state.game
            except Game.DoesNotExist:
                yield defer_to_thread(self.player_state.refresh_from_db)

    @inline_callbacks
    def _disconnect_from_game(self):
        if self.player_state.game:
            self.connection.factory.unregister_from_group(self.player_state.game.key, self.connection)
            self.connection.queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data={
                    "player_id": self.player_state.key
                },
                group_name=self.player_state.game.key
            )

            defer_to_thread(self.player_state.quit_game)

    @inline_callbacks
    def on_disconnect(self):
        self.refresh_state()
        yield self._disconnect_from_game()

        yield defer_to_thread(remove_logged_player, self.player_state.snap_id)

    @inline_callbacks
    def position_update(self, message):
        if self.player_state.game:
            serializer = PlayerTransformSerializer({'key': self.player_state.key, **message})
            yield defer_to_thread(
                update_player_game_data_cache,
                self.player_state.snap_id,
                self.player_state.game.key,
                serializer.data
            )

    @inline_callbacks
    def quit_game(self, _):
        if self.player_state.game:
            self.connection.factory.unregister_from_group(self.player_state.game.key, self.connection)
            self.connection.queue_to_broadcast(
                RESPONSE_PLAYER_LEFT,
                data={
                    "player_id": self.player_state.snap_id
                },
                group_name=self.player_state.game.key
            )
            yield defer_to_thread(self.player_state.quit_game)
