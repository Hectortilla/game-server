import logging
from django.db import models
logger = logging.getLogger(__name__)


class PlayerManager(models.Manager):
    def auth(self, name):
        player, _ = self.get_or_create(name=name)
        return player, None
