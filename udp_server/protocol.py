#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json
from django.apps import apps
from colorama import Fore
from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.threads import deferToThread as defer_to_thread
from twisted.logger import Logger

from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread
from apps.cache import (add_logged_player, get_logged_players, get_message_for_client, flush_all,
                        add_to_group, remove_from_group, add_single_message_to_broadcast,
                        get_message_queued_for_client, get_clients_from_group, add_message_to_broadcast_queue)

from apps.players.models import Player as PlayerState
from apps.players.serializers import (AuthSerializer, SendAuthSerializer)
from udp_server.player import Player

from settings import RESPONSE_PLAYER_ALREADY_LOGGED, RESPONSE_AUTH_FAILURE, RESPONSE_AUTH_PLAYER, RESPONSE_PONG


logger = Logger()


# Here's a UDP version of the simplest possible protocol
class SocketProtocol(DatagramProtocol):
    register_action = 'auth'
    ignore_actions = ["move", "PLAYERS_TRANSFORM"]
    connections = {}

    def __init__(self, service):
        self.service = service
        self.actions = {
            "auth": self.auth,
            "ping": self.ping
        }
        DatagramProtocol.__init__(self)
        self.reset_db()

    def send_error(self, address, msg):
        datagram = json.dumps({'action': 'error', 'data': msg}).encode()
        self.transport.write(datagram, address)

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
        self.transport.write(datagram, address)

    @inline_callbacks
    def add_to_group(self, group_name, sender):
        yield defer_to_thread(add_to_group, group_name, sender)

    @inline_callbacks
    def unregister_from_group(self, group_name, sender):
        yield defer_to_thread(remove_from_group, group_name, sender)

    @inline_callbacks
    def datagramReceived(self, datagram, address):
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

        if action in self.actions:
            sent = True
            yield self.actions[action](data, address)

        if self.connections.get(address) and action in self.connections[address].actions:
            sent = True
            yield self.connections[address].execute_action(action, data)

        if action in self.service.actions:
            sent = True
            yield self.service.actions[action](self, data, address)

        if not sent:
            self.send_error(address, "Action {} not allowed".format(action))

    @inline_callbacks
    def auth(self, message, address):
        if self.connections.get(address) is not None:
            return

        serializer = AuthSerializer(data=message)
        if not serializer.is_valid():
            self.send_error(address, serializer.errors)
            return

        player_state, error = yield defer_to_thread(
            PlayerState.objects.auth,
            serializer.data['name']
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
        # yield defer_to_thread(set_player_to_client, player_state.key, self.key)

        self.connections[address] = Player(self, player_state, address)

        serializer = SendAuthSerializer(player_state)

        self.send(
            address,
            RESPONSE_AUTH_PLAYER,
            data=serializer.data
        )
        yield self.connections[address].join_game()

    @inline_callbacks
    def ping(self, _, address):
        yield
        self.send(address, RESPONSE_PONG, data={"message": "pong"})

    # ------------------------ Send
    @inline_callbacks
    def queue_to_broadcast(self, action, data=None, exclude_sender=False, sender=None, group_name=None):
        if not group_name:
            raise Exception("We need a group name to broadcast!")
        group_clients = yield defer_to_thread(get_clients_from_group, group_name)
        for _sender in group_clients:
            if exclude_sender and sender == _sender:
                continue
            yield defer_to_thread(add_message_to_broadcast_queue, _sender, action, data)

    @inline_callbacks
    def single_message_to_broadcast(self, action, data=None, exclude_sender=True, sender=None, group_name=None):
        if not group_name:
            raise Exception("We need a group name to broadcast!")
        group_clients = yield defer_to_thread(get_clients_from_group, group_name)
        for client_id in group_clients:
            if exclude_sender and sender == client_id:
                continue
            yield defer_to_thread(add_single_message_to_broadcast, client_id, action, data)

    @inline_callbacks
    def consume_queued_broadcast_messages(self):
        for client in self.connections:
            action, data = get_message_for_client(self.connections[client].address_key)
            if action:
                self.send(self.connections[client].address, action=action, data=data)
            messages = yield defer_to_thread(get_message_queued_for_client, self.connections[client].address_key)
            for action, data in messages:
                self.send(self.connections[client].address, action=action, data=data)

    # ------------------------ reset
    def reset_db(self):
        Player = apps.get_model('players', 'Player')
        Game = apps.get_model('games', 'Game')
        for player in Player.objects.all():
            player.game = None
            player.save()
        Game.objects.all().delete()
        flush_all()
