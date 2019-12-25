import os
from configparser import ConfigParser

import django
from environment import settings, environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.%s" % environment)
django.setup()

from twisted.application import service
from twisted.application.service import Application, IServiceMaker
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implementer


from udp_server.service import GameServerService


class Options(usage.Options):
    pass


@implementer(IServiceMaker, IPlugin)
class GameServerServiceMaker(object):
    tapname = 'udp-game-server'
    description = 'UDP GameServer server'
    options = Options

    def makeService(self, options):
        """ called by 'python -m twisted -no game-server',
            via twisted.plugins.game_server_plugin
        """
        # config = ConfigParser()
        # config.read([options['config']])

        application = Application(settings.UDP_SERVER_NAME)

        main = service.MultiService()

        game_server_service = GameServerService()
        game_server_service.setName(settings.UDP_SERVER_NAME)
        game_server_service.setServiceParent(main)

        main.setServiceParent(application)
        return main
