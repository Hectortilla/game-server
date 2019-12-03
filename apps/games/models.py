import time

from django.apps import apps
from django.db import models
from django.utils.timezone import now


from apps.games.managers import GameManager
from apps.main.model_mixins import ModelMixinBundle


class Game(ModelMixinBundle):
    objects = GameManager()
    seed = models.BigIntegerField(null=False)
