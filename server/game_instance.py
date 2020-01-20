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
        self.protocol.queue_to_broadcast(
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

    '''
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
    '''
