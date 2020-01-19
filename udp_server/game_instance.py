import logging

from django.conf import settings
from django.db import IntegrityError
from twisted.application import service
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread
from django.apps import apps

from apps.cache import (
    remove_players_game_data,
    set_dirty,
    remove_game,
    list_players_of_game)
from apps.players.serializers import (
    GamePlayersSerializer, GameJoinedSerializer, PlayerJoinedGameSerializer)
# from apps.players.models import Player
from settings.constants import (
    RESPONSE_JOINED_GAME, RESPONSE_GAME_PLAYERS, RESPONSE_PLAYER_JOINED)

logger = logging.getLogger()

position_update_interval = 0


class GameInstance(service.Service):

    def __init__(self, service, protocol, game_state):
        self.finished = False
        self.service = service
        self.protocol = protocol

        self.game_state = game_state
        self.key = self.game_state.key
        self.players = []

        call_later(1, self.check_for_new_players)

    @inline_callbacks
    def add_player(self, player_key):
        Player = apps.get_model('players', 'Player')
        player = yield Player.objects.get(key=player_key)
        yield self.protocol.add_to_group(self.game_state.key, player.address)
        data = {
            "players": GamePlayersSerializer(self.game_state.get_players(), many=True).data
        }
        self.protocol.send(player.address, RESPONSE_JOINED_GAME, data=GameJoinedSerializer(self.game_state).data)
        self.protocol.send(player.address, RESPONSE_GAME_PLAYERS, data=data)
        self.protocol.queue_to_broadcast(
            RESPONSE_PLAYER_JOINED,
            exclude_sender=True,
            data=PlayerJoinedGameSerializer(player.player_state).data,
            address=player.address,
            group_name=player.player_state.game.key
        )

    @inline_callbacks
    def check_for_new_players(self):
        players = yield defer_to_thread(list_players_of_game, self.game_state.key)
        for player_key in players:
            if player_key not in self.players:
                yield self.add_player(player_key)
        call_later(1, self.check_for_new_players)

    '''
    @inline_callbacks
    def check_for_ready_to_start(self):
        # TODO: check for max wait, if a player is not ready, kick him
        ready_to_start = yield defer_to_thread(self.game_state.set_ready_to_start)
        if ready_to_start:
            yield self.count_down()
        else:
            call_later(settings.CHECK_FOR_READY_GAMES_INTERVAL, self.check_for_ready_to_start)

    @inline_callbacks
    def count_down(self):
        log(f'🚀 Count-down {self.key}')

        yield self.protocol.queue_to_broadcast(
            RESPONSE_COUNT_DOWN,
            None,
            data={'time_left': MAX_TIME_LEFT},
            exclude_sender=False,
            group_name=self.key
        )
        call_later(MAX_TIME_LEFT, self.start)

    @inline_callbacks
    def start(self):
        log(f'🚀 Start {self.key}')

        self.status = GAME_STATE_STARTED
        yield self.protocol.queue_to_broadcast(
            RESPONSE_GAME_STARTED,
            None,
            exclude_sender=False,
            group_name=self.key
        )
        if settings.DEV:
            call_later(0, self.update_settings, force=True)

        call_later(2, self.game_status)

    @inline_callbacks
    def update_settings(self, force=False):
        if self.finished:
            return

        _game_settings_changed = yield defer_to_thread(game_settings_changed)
        if _game_settings_changed or force:
            global position_update_interval
            game_settings = yield defer_to_thread(GameSettings.objects.get_settings)
            position_update_interval = game_settings.position_update_interval
            yield defer_to_thread(set_game_settings_unchanged)

        if self.status != GAME_STATE_COMPLETE:
            call_later(1, self.update_settings)

    @inline_callbacks
    def game_status(self):
        if self.finished:
            return

        players = yield defer_to_thread(self.game_state.get_players)
        if self.game_state.state == GAME_STATE_COMPLETE and not players:
            self.game_state.delete()
            yield defer_to_thread(remove_players_game_data, self.key)
            yield self.protocol.remove_group(self.key)
            log(f'🏁 Stop {self.key}')
            self.stopService()

        else:
            all_dead = yield defer_to_thread(
                self.game_state.all_players_dead
            )

            if all_dead:
                self.game_state.state = GAME_STATE_COMPLETE
                yield defer_to_thread(self.game_state.save)

                for player in self.players:
                    player.state = PLAYER_STATE_LOADING
                    player.game = None
                    try:
                        yield defer_to_thread(player.save, update_fields=["state", "game"])
                    except IntegrityError:
                        continue
                    yield defer_to_thread(set_dirty, player.snap_id)

                yield self.protocol.queue_to_broadcast(
                    RESPONSE_GAME_FINISHED,
                    None,
                    data={},
                    group_name=self.key
                )

                yield defer_to_thread(remove_game, self.key)
                self.service.remove_game(self)
                self.finished = True

            call_later(2, self.game_status)
    '''
