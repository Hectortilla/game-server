import logging
from django.apps import apps
from django.db import models

from apps.cache import add_player_to_game, remove_player_from_game
from apps.main.model_mixins import ModelMixinBundle
from apps.players.managers import PlayerManager

logger = logging.getLogger(__name__)


class Player(ModelMixinBundle):
    objects = PlayerManager()

    name = models.CharField(unique=True, max_length=32, db_index=True)
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
        remove_player_from_game(self.game.key, self.key)
        self.game = None
        self.save()

    def add_to_default_game(self):
        Game = apps.get_model('games', 'Game')
        game, created = Game.objects.get_or_create(seed=0)
        '''
        if created:
            add_game(game.key)
        '''
        add_player_to_game(game.key, self.key)

        self.game = game
        self.save()
        return game, game.get_players()
