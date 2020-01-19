from django.db import models


class GameManager(models.Manager):
    def get_or_create(self, **kwargs):
        empty = True
        obj, created = super().get_or_create(**kwargs)
        if obj.get_players():
            empty = False

        return obj, created, empty

