from twisted.internet.defer import inlineCallbacks as inline_callbacks
from twisted.internet.threads import deferToThread as defer_to_thread

from apps.cache import get_clients_from_group, add_message_to_broadcast_queue


@inline_callbacks
def queue_to_broadcast(self, action, data=None, exclude_sender=False, address=None, group_name=None):
    if not group_name:
        raise Exception("We need a group name to broadcast!")
    group_clients = yield defer_to_thread(get_clients_from_group, group_name)
    for _address in group_clients:
        if exclude_sender and address == _address:
            continue
        yield defer_to_thread(add_message_to_broadcast_queue, _address, action, data)
