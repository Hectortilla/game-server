from django.db import models
from apps.players.models import Player

from apps.games.managers import GameManager
from apps.main.model_mixins import ModelMixinBundle


class Game(ModelMixinBundle):
    objects = GameManager()
    seed = models.BigIntegerField(null=False)

    def get_players(self):
        return Player.objects.filter(game=self)
