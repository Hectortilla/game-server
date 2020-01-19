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


from udp_server.game_service import GameService
from twisted.application import internet
from udp_server.protocol import GameProtocol


class Options(usage.Options):
    pass


@implementer(IServiceMaker, IPlugin)
class GameServerServiceMaker(object):
    tapname = 'udp-game-server'
    description = 'UDP Game Server'
    options = Options

    def makeService(self, options):
        """ called by 'python -m twisted -no game-server',
            via twisted.plugins.game_server_plugin
        """
        # config = ConfigParser()
        # config.read([options['config']])

        application = Application(settings.SERVER_NAME)
        main = service.MultiService()

        game_service = GameService()
        game_service.setName(settings.SERVER_NAME + '-game-service')
        game_service.setServiceParent(main)

        game_protocol = GameProtocol(game_service)
        udp_service = internet.UDPServer(settings.SOCKET_SERVER_PORT, game_protocol)
        udp_service.setName(settings.SERVER_NAME + '-udp-service')
        udp_service.setServiceParent(main)


        main.setServiceParent(application)
        return main
