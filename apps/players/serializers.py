from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers


class AuthSerializer(serializers.Serializer):
    name = serializers.CharField()


class SendAuthSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()


class PlayerTransformSerializer(serializers.Serializer):
    key = serializers.CharField()

    px = serializers.FloatField()
    py = serializers.FloatField()
    pz = serializers.FloatField()

    rx = serializers.FloatField()
    ry = serializers.FloatField()
    rz = serializers.FloatField()


class SendPlayerTransformSerializer(serializers.Serializer):
    key = serializers.CharField()

    px = serializers.FloatField()
    py = serializers.FloatField()
    pz = serializers.FloatField()

    rx = serializers.FloatField()
    ry = serializers.FloatField()
    rz = serializers.FloatField()


class PlayerMovedSerializer(serializers.Serializer):
    px = serializers.FloatField()
    py = serializers.FloatField()
    pz = serializers.FloatField()

    rx = serializers.FloatField()
    ry = serializers.FloatField()
    rz = serializers.FloatField()


class PlayerJoinedGameSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()


class PlayerLeftGameSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()


class GamePlayersSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()


class GameJoinedSerializer(serializers.Serializer):
    key = serializers.CharField()
