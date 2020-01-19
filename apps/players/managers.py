import logging
from django.db import models
logger = logging.getLogger(__name__)


class PlayerManager(models.Manager):
    def auth(self, name, address):
        player, _ = self.get_or_create(name=name, address=address)  # TODO: Get by name first
        player.save()
        return player, None
