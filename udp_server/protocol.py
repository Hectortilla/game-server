#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
from colorama import Fore

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.logger import Logger

logger = Logger()


# Here's a UDP version of the simplest possible protocol
class SocketProtocol(DatagramProtocol):
    def __init__(self, service):
        self.service = service
        DatagramProtocol.__init__(self)

    def datagramReceived(self, datagram, address):
        logger.info(Fore.RED + '\u21E6' + Fore.RESET + ' Receivning ::: {}'.format(datagram))
        self.transport.write(datagram, address)
