import json

from django.conf import settings
from redis import Redis

from settings.constants import (BROADCAST_QUEUE_CACHE_PREFIX,
                      GROUP_CACHE_PREFIX,
                      LOGGED_PLAYERS_CACHE_PREFIX,
                      PLAYER_STATE_DIRTY_CACHE_PREFIX)

redis_connection = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


USER_KEYS = ['key', 'px', 'py', 'pz', 'rx', 'ry', 'rz']


def get_logged_players_key():
    return LOGGED_PLAYERS_CACHE_PREFIX


def get_player_state_dirty_key(player_key):
    return f'{PLAYER_STATE_DIRTY_CACHE_PREFIX}:{player_key}'


def get_broadcast_queue_key(player_key):
    return f'{BROADCAST_QUEUE_CACHE_PREFIX}:{player_key}'


def get_group_cache_key(group_name):
    return f'{GROUP_CACHE_PREFIX}:{group_name}'


# --- flushing all for when starting the server ---

def flush_all():
    redis_connection.flushall()


# --- logging ---

def add_logged_player(player_key):
    redis_connection.sadd(
        get_logged_players_key(), player_key
    )


def remove_logged_player(player_key):
    redis_connection.srem(get_logged_players_key(), player_key)
    redis_connection.delete(get_player_state_dirty_key(player_key))


def get_logged_players():
    return redis_connection.smembers(get_logged_players_key())


# --- player state ---

def set_dirty(key):
    redis_connection.set(
        get_player_state_dirty_key(key), 1
    )


def set_clean(key):
    redis_connection.set(
        get_player_state_dirty_key(key), 0
    )


def is_dirty(key):
    return int(redis_connection.get(
        get_player_state_dirty_key(key)
    ) or 0)


# --- broadcasting ---

def add_message_to_broadcast_queue(client_id, action, message):
    redis_connection.rpush(get_broadcast_queue_key(client_id), json.dumps({'action': action, 'message': message}))


def get_message_queued_for_client(client_id):
    msg = redis_connection.lpop(get_broadcast_queue_key(client_id))
    while msg:
        msg = json.loads(msg)
        yield msg['action'], msg['message']
        msg = redis_connection.lpop(get_broadcast_queue_key(client_id))


def remove_broadcast_queue(client_id):
    redis_connection.delete(get_broadcast_queue_key(client_id))


# --- groups ---

def add_to_group(group_name, address):
    redis_connection.sadd(get_group_cache_key(group_name), address)


def get_clients_from_group(group_name):
    return redis_connection.smembers(get_group_cache_key(group_name))


def remove_from_group(group_name, client_id):
    redis_connection.srem(get_group_cache_key(group_name), client_id)


def delete_group(group_name):
    redis_connection.delete(get_group_cache_key(group_name))
