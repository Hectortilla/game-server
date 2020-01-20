import logging
from django.apps import apps
from django.db import models

from apps.main.model_mixins import ModelMixinBundle
from apps.players.managers import PlayerManager
from server.game_instance import GameInstance

logger = logging.getLogger(__name__)


class Player(ModelMixinBundle):
    objects = PlayerManager()

    name = models.CharField(unique=True, max_length=32, db_index=True)
    address = models.GenericIPAddressField(unique=True, db_index=True)
    game = models.ForeignKey('games.Game', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        # Settings
        self.px = 0
        self.py = 0
        self.pz = 0

        self.rx = 0
        self.ry = 0
        self.rz = 0

        super(Player, self).__init__(*args, **kwargs)

    def quit_game(self):
        self.game = None
        self.save()
