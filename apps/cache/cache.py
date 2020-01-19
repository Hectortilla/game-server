import json
import sys

from django.apps import apps
from django.conf import settings
from django.forms.models import model_to_dict
from redis import Redis

from settings.constants import (BROADCAST_QUEUE_CACHE_PREFIX, BROADCAST_CACHE_PREFIX,
                      GAMES_CACHE_PREFIX, GROUP_CACHE_PREFIX,
                      LOGGED_PLAYERS_CACHE_PREFIX, MATCHING_ROOMS_CACHE_PREFIX,
                      PLAYER_COINS_CACHE_PREFIX, PLAYER_DATA_CACHE_PREFIX,
                      PLAYER_STATE_DIRTY_CACHE_PREFIX,
                      PLAYER_TO_CLIENT_CACHE_PREFIX,
                      PLAYERS_IN_GAME_CACHE_PREFIX)

redis_connection = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)


USER_KEYS = ['key', 'px', 'py', 'pz', 'rx', 'ry', 'rz']


def get_games_key():
    return GAMES_CACHE_PREFIX


def get_logged_players_key():
    return LOGGED_PLAYERS_CACHE_PREFIX


def get_player_game_data_key(player_key, game_key):
    return f'{PLAYER_DATA_CACHE_PREFIX}:{player_key}:{game_key}:data'


def get_players_in_game_key(game_key):
    return f'{PLAYERS_IN_GAME_CACHE_PREFIX}:{game_key}'


def get_player_state_dirty_key(player_key):
    return f'{PLAYER_STATE_DIRTY_CACHE_PREFIX}:{player_key}'


def get_matching_rooms_key():
    return MATCHING_ROOMS_CACHE_PREFIX


def get_broadcast_queue_key(player_key):
    return f'{BROADCAST_QUEUE_CACHE_PREFIX}:{player_key}'


def get_broadcast_key(player_key):
    return f'{BROADCAST_CACHE_PREFIX}:{player_key}'


def get_group_cache_key(group_name):
    return f'{GROUP_CACHE_PREFIX}:{group_name}'


def get_player_to_client_key(player_key):
    return f'{PLAYER_TO_CLIENT_CACHE_PREFIX}:{player_key}'


# --- DATA OF PLAYERS (POS, SPEED, CHANNEL, ETC...) ---

def update_player_game_data_cache(game_key, player_key, data):
    user_hash_key = get_player_game_data_key(player_key, game_key)
    redis_connection.hmset(user_hash_key, data)


def remove_player_info(player_key, game_key):
    redis_connection.delete(
        get_player_game_data_key(player_key, game_key)
    )

# --- PLAYER LOGGING


def add_logged_player(player_key):
    redis_connection.sadd(
        get_logged_players_key(), player_key
    )


def remove_logged_player(player_key):
    redis_connection.srem(get_logged_players_key(), player_key)
    redis_connection.delete(get_player_state_dirty_key(player_key))


def get_logged_players():
    return redis_connection.smembers(get_logged_players_key())


# --- SET OF ACTIVE GAMES ---

'''
def add_game(game_key):
    redis_connection.sadd(
        get_games_key(), game_key
    )


def list_games():
    return redis_connection.smembers(get_games_key())


def remove_game(game_key):
    return redis_connection.srem(get_games_key(), game_key)
'''


def remove_players_game_data(game_key):
    for player_key in list_players_of_game(game_key):
        user_hash_key = get_player_game_data_key(player_key, game_key)
        redis_connection.delete(user_hash_key)
    delete_group(game_key)
    redis_connection.delete(get_players_in_game_key(game_key))

# --- PLAYERS PER GAME ---


def get_game_players_data(game_key):
    res = []
    player_keys = list_players_of_game(game_key)
    for player_key in player_keys:
        user_hash_key = get_player_game_data_key(player_key, game_key)
        player = redis_connection.hgetall(user_hash_key)
        if player and player.get('key'):
            res.append(player)

    return res


def add_player_to_game(game_key, player_key):
    redis_connection.sadd(
        get_players_in_game_key(game_key), player_key
    )


def list_players_of_game(game_key):
    return redis_connection.smembers(
        get_players_in_game_key(game_key)
    )


def remove_player_from_game(game_key, player_key):
    redis_connection.srem(
        get_players_in_game_key(game_key), player_key
    )
    user_hash_key = get_player_game_data_key(player_key, game_key)
    redis_connection.delete(user_hash_key)


# --- Matchmaking ---

def set_matching_rooms(matching_rooms):
    keys = []
    for matching_room in matching_rooms:
        keys.append(matching_room)

    redis_connection.rpush(
        get_matching_rooms_key(), json.dumps(keys)
    )


def get_matching_rooms():
    res = redis_connection.lpop(
        get_matching_rooms_key()
    )
    while res:
        yield res
        res = redis_connection.lpop(
            get_matching_rooms_key()
        )


def flush_all():
    redis_connection.flushall()

# --- State ---


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


def set_player_to_client(player_key, client_id):
    redis_connection.set(get_player_to_client_key(player_key), client_id)


def get_client_from_player(player_key):
    return redis_connection.get(get_player_to_client_key(player_key))


def delete_player_to_client(player_key):
    redis_connection.delete(get_player_to_client_key(player_key))


def add_message_to_broadcast_queue(client_id, action, message):
    redis_connection.rpush(get_broadcast_queue_key(client_id), json.dumps({'action': action, 'message': message}))


def add_single_message_to_broadcast(client_id, action, message):
    redis_connection.set(get_broadcast_key(client_id), json.dumps({'action': action, 'message': message}))


def get_message_queued_for_client(client_id):
    msg = redis_connection.lpop(get_broadcast_queue_key(client_id))
    while msg:
        msg = json.loads(msg)
        yield msg['action'], msg['message']
        msg = redis_connection.lpop(get_broadcast_queue_key(client_id))


def get_message_for_client(client_id):
    redis_connection_p = redis_connection.pipeline()
    redis_connection_p.get(get_broadcast_key(client_id))
    redis_connection_p.delete(get_broadcast_key(client_id))
    msg = redis_connection_p.execute()
    if msg[0]:
        msg = json.loads(msg[0])
        return msg['action'], msg['message']
    else:
        return None, None


def add_to_group(group_name, client_id):
    redis_connection.sadd(get_group_cache_key(group_name), client_id)


def get_clients_from_group(group_name):
    return redis_connection.smembers(get_group_cache_key(group_name))


def remove_from_group(group_name, client_id):
    redis_connection.srem(get_group_cache_key(group_name), client_id)


def delete_group(group_name):
    redis_connection.delete(get_group_cache_key(group_name))


def remove_broadcast_queue(client_id):
    redis_connection.delete(get_broadcast_queue_key(client_id))
