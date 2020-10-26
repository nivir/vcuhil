# Simple Telnet Interface
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports

from __future__ import print_function

import logging

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.conch.telnet import StatefulTelnetProtocol, TelnetTransport
from twisted.internet import reactor


log = logging.getLogger('VCUHIL')


class TelnetClient(StatefulTelnetProtocol):
    def __init__(self):
        self.command_deferred = None

        self.command = b''
        self.response = b''

        self.done_callback = None

    def connectionMade(self):
        """
        Set rawMode since we do not receive the login and password prompt in line mode.
        We return to default line mode when we detect the prompt in the received data stream.
        """
        print('Telnet client logged in. We are ready for commands')
        self.setLineMode()

    def lineReceived(self, line):
        # ignore data sent by server before command is sent
        # ignore command echo from server
        if not self.command or line == self.command:
            return

        # trim control characters
        if line.startswith(b'\x1b'):
            line = line[4:]

        print('Received telnet line: %s' % repr(line))

        self.response += line + b'\r\n'

        # start countdown to command done (when reached, consider the output was completely received and close)
        if not self.done_callback:
            self.done_callback = reactor.callLater(0.5, self.close)
        else:
            self.done_callback.reset(0.5)

    def send_command(self, command):
        """
        Sends a command via Telnet using line mode
        """
        self.command = f'{command}\r'
        self.command = command.encode()
        self.sendLine(self.command)

    def close(self):
        """
        Sends exit to the Telnet server and closes connection.
        Fires the deferred with the command's output.
        """
        self.sendLine(b'exit')
        self.factory.transport.loseConnection()

        # third deferred, to signal command's output was fully received
        self.command_deferred.callback(self.response)


class TelnetClientFactory(ReconnectingClientFactory):
    def startedConnecting(self, connector):
        log.debug('Started to connect.')

    def buildProtocol(self, addr):
        self.transport = TelnetTransport(TelnetClient)
        self.transport.factory = self
        return self.transport

    def clientConnectionLost(self, connector, reason):
        log.info(f'Lost Connection.  Reason: {reason}')
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.info(f'Failed Connection.  Reason: {reason}')
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)
