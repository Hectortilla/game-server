from django.db import models
from apps.cache import is_dirty


class GameManager(models.Manager):
    def add_to_default_game(self, player):
        game = self.get_or_create(seed=0)
        self.player_state.game = game
        self.player_state.save()
        is_dirty(player.key)
        return game
