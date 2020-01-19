from django.db import models
from apps.players.models import Player

from apps.games.managers import GameManager
from apps.main.model_mixins import ModelMixinBundle
from apps.cache import add_player_to_game


class Game(ModelMixinBundle):
    objects = GameManager()
    seed = models.BigIntegerField(null=False)

    def get_players(self):
        return Player.objects.filter(game=self)

    @classmethod
    def matchmake(cls, player):
        game, created, empty = cls.objects.get_or_create(seed=0)
        if empty:
            pass
            # ad_service
        add_player_to_game(game.key, player.key)
        player.game = game
        player.save()
        return game, game.get_players()
