import logging

from django.conf import settings
from django.db import IntegrityError
from twisted.application import service
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.reactor import callLater as call_later
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import (
    remove_players_game_data,
    set_dirty,
    remove_game
)
from apps.game_settings.models import GameSettings
from apps.players.models import Player
from apps.players.serializers import (
    SendPlayerInfoSerializer
)

from settings.constants import (
    GAME_STATE_WAITING,
    RESPONSE_COUNT_DOWN,
    MAX_TIME_LEFT,
    RESPONSE_GAME_STARTED,
    GAME_STATE_STARTED,
    GAME_STATE_COMPLETE,
    RESPONSE_GAME_FINISHED,
    PLAYER_STATE_LOADING,
    RESPONSE_GAME_INFO,
    RESPONSE_FULL_ROOM
)
from tools import log

logger = logging.getLogger()

position_update_interval = 0


class GameInstance(service.Service):

    def __init__(self, service, state):
        self.finished = False
        self.service = service
        self.protocol = service.protocol

        self.status = GAME_STATE_WAITING

        self.state = state
        self.key = self.state.key

        self.setup()

    @inline_callbacks
    def setup(self):
        # called in thread by matchmaker-service

        def _get_players_from_room(waiting_room):
            return list(Player.objects.filter(temp_room=waiting_room).order_by('connected_to_game_time'))

        for waiting_room in waiting_rooms:
            players = yield defer_to_thread(_get_players_from_room, waiting_room)

            for player in players:
                player.game = self.state
                player.state = PLAYER_STATE_LOADING
                yield defer_to_thread(player.save)
                yield defer_to_thread(set_dirty, player.snap_id)

        self.players = yield defer_to_thread(self.state.get_players)
        serializer = yield defer_to_thread(SendPlayerInfoSerializer, self.players, many=True)

        data = list(serializer.data)
        for index, player in enumerate(data):
            # data[index]['current_lane'] = get_player_cache_info(player['id'], self.key, [('current_lane', int)])
            data[index]['current_lane'] = index

        yield self.protocol.queue_to_broadcast(
            RESPONSE_GAME_INFO,
            None,
            data={'players': data, 'settings': data},
            group_name=self.key
        )
        yield self.protocol.queue_to_broadcast(
            RESPONSE_FULL_ROOM,
            None, data={},
            exclude_sender=False,
            group_name=self.key
        )
        call_later(settings.CHECK_FOR_READY_GAMES_INTERVAL, self.check_for_ready_to_start)

    @inline_callbacks
    def check_for_ready_to_start(self):
        # TODO: check for max wait, if a player is not ready, kick him
        ready_to_start = yield defer_to_thread(self.state.set_ready_to_start)
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

        players = yield defer_to_thread(self.state.get_players)
        if self.state.state == GAME_STATE_COMPLETE and not players:
            self.state.delete()
            yield defer_to_thread(remove_players_game_data, self.key)
            yield self.protocol.remove_group(self.key)
            log(f'🏁 Stop {self.key}')
            self.stopService()

        else:
            all_dead = yield defer_to_thread(
                self.state.all_players_dead
            )

            if all_dead:
                self.state.state = GAME_STATE_COMPLETE
                yield defer_to_thread(self.state.save)

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

