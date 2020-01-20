#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json
import time
from django.apps import apps
from colorama import Fore
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread as defer_to_thread
from twisted.logger import Logger

from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread
from apps.cache import (add_logged_player, get_logged_players, flush_all,
                        add_to_group, remove_from_group,
                        get_message_queued_for_client, get_clients_from_group, add_message_to_broadcast_queue,
                        remove_logged_player, remove_broadcast_queue)

from apps.players.models import Player as PlayerState
from apps.players.serializers import (AuthSerializer, SendAuthSerializer)
from server.player import Player
from twisted.internet.reactor import callLater as call_later

from settings import RESPONSE_PLAYER_ALREADY_LOGGED, RESPONSE_AUTH_FAILURE, RESPONSE_AUTH_PLAYER, RESPONSE_PONG
import threading

lock = threading.Lock()

logger = Logger()


class GameProtocol(DatagramProtocol):
    disconnect_action = 'disconnect'
    ignore_actions = ["move", "PLAYERS_TRANSFORM"]
    connections = {}

    def __init__(self, game_service):
        self.game_service = game_service
        self.actions = {
            "auth": self.auth,
            "ping": self.ping
        }
        DatagramProtocol.__init__(self)
        self.reset_db()

        call_later(0, self.consume_broadcast_messages)
        call_later(0, self.check_disconnect)

    def send_error(self, address, msg):
        datagram = json.dumps({'action': 'error', 'data': msg}).encode()

        address_tpl = (address.split(':')[0], int(address.split(':')[1]), )
        self.transport.write(datagram, address_tpl)

    def send(self, address, action, data={}):
        if action not in self.ignore_actions:
            if action == 'error':
                logger.info(Fore.GREEN + '\u2192' + Fore.RESET + ' Sending ::: {} - Data {}'.format(action, data))
            else:
                logger.info(Fore.GREEN + '\u2192' + Fore.RESET + ' Sending ::: {}'.format(action))

        if data is None:
            data = {}
        response = {'action': action, 'data': json.dumps(data)}
        datagram = json.dumps(response).encode('utf8')

        address_tpl = (address.split(':')[0], int(address.split(':')[1]), )
        self.transport.write(datagram, address_tpl)

    @inline_callbacks
    def datagramReceived(self, datagram, address):
        address = address[0] + ':' + str(address[1])
        self.update_connection(address)

        msg = json.loads(datagram.decode("utf-8"))

        try:
            msg = json.loads(datagram.decode('utf8'))
        except ValueError:
            self.send_error(address, {'message': 'Invalid JSON.'})
            return

        if 'action' not in msg:
            self.send_error(address, {'message': 'Action needed.'})
            return
        try:
            data = json.loads(msg.get('data', {}))
        except ValueError:
            self.send_error(address, {'message': 'Invalid JSON.'})
            return

        action = msg['action']
        sent = False

        if action not in self.ignore_actions:
            logger.info(Fore.RED + '\u21E6' + Fore.RESET + ' Receivning ::: {}'.format(action))

        if action == self.disconnect_action:
            self.disconnnect(address)
            return

        if action in self.actions:
            sent = True
            yield self.actions[action](data, address)

        if self.connections.get(address) and self.connections[address].get('player') and action in self.connections[address]['player'].actions:
            sent = True
            yield self.connections[address]['player'].execute_action(action, data)

        '''
        if action in self.service.actions:
            sent = True
            yield self.service.actions[action](self, data, address)
        '''

        if not sent:
            self.send_error(address, "Action {} not allowed".format(action))

    # --------------------------- Connection health

    def update_connection(self, address):
        if address not in self.connections:
            # lock.acquire()
            self.connections[address] = {'t': time.time()}
            # lock.release()
        else:
            self.connections[address]['t'] = time.time()

    @inline_callbacks
    def check_disconnect(self):
        for address, conn_data in list(self.connections.items()):
            if time.time() - conn_data['t'] > 10:
                yield self.disconnnect(address)

        call_later(1, self.check_disconnect)

    @inline_callbacks
    def disconnnect(self, address):
        if self.connections[address].get('player'):
            yield defer_to_thread(remove_logged_player, self.connections[address]['player'].player_state.key)
            yield self.connections[address]['player'].on_disconnect()
            # yield defer_to_thread(delete_player_to_client, self.connections[address]['player'].player_state.key)
            yield defer_to_thread(remove_broadcast_queue, self.connections[address]['player'].player_state.address)
        # if self.connections[address]['player']:
        #     yield defer_to_thread(set_authenticable, self.connections[address]['player'].state.key)
        # lock.acquire()
        del self.connections[address]
        # lock.release()
    # --------------------------- Actions

    @inline_callbacks
    def auth(self, message, address):
        if self.connections.get(address).get('player') is not None:
            return
        serializer = AuthSerializer(data=message)
        if not serializer.is_valid():
            self.send_error(address, serializer.errors)
            return

        player_state, error = yield defer_to_thread(
            PlayerState.objects.auth,
            serializer.data['name'],
            address
        )
        if not player_state:
            self.send(RESPONSE_AUTH_FAILURE, data=error)
            return

        logged_players = yield defer_to_thread(get_logged_players)
        if player_state.key in logged_players:
            self.send(
                RESPONSE_PLAYER_ALREADY_LOGGED,
                data=serializer.data['name']
            )

        yield defer_to_thread(add_logged_player, player_state.key)

        self.connections[address]['player'] = Player(self, player_state)

        serializer = SendAuthSerializer(player_state)

        self.send(
            address,
            RESPONSE_AUTH_PLAYER,
            data=serializer.data
        )
        yield self.game_service.matchmake(self.connections[address]['player'])

    @inline_callbacks
    def ping(self, _, address):
        yield
        self.send(address, RESPONSE_PONG, data={"message": "pong"})

    # ------------------------ Send
    @inline_callbacks
    def queue_to_broadcast(self, action, data=None, exclude_sender=False, address=None, group_name=None):
        if not group_name:
            raise Exception("We need a group name to broadcast!")
        group_clients = yield defer_to_thread(get_clients_from_group, group_name)
        for _address in group_clients:
            if exclude_sender and address == _address:
                continue
            yield defer_to_thread(add_message_to_broadcast_queue, _address, action, data)

    @inline_callbacks
    def consume_broadcast_messages(self):
        for address, conn_data in list(self.connections.items()):
            if conn_data.get('player'):
                action, data = yield defer_to_thread(get_message_for_client, conn_data['player'].player_state.address)
                if action:
                    self.send(address, action=action, data=data)
                messages = yield defer_to_thread(get_message_queued_for_client, conn_data['player'].player_state.address)
                for action, data in messages:
                    self.send(address, action=action, data=data)

        call_later(0, self.consume_broadcast_messages)

    # ------------------------ reset
    def reset_db(self):
        Player = apps.get_model('players', 'Player')
        Game = apps.get_model('games', 'Game')
        for player in Player.objects.all():
            player.game = None
            player.save()
        Game.objects.all().delete()
        flush_all()
