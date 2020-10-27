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
        self.response_deferred = None
        self.response_required = False

        self.command = b''
        self.response = b''

        self.done_callback = None

    def connectionMade(self):
        """
        Set rawMode since we do not receive the login and password prompt in line mode.
        We return to default line mode when we detect the prompt in the received data stream.
        """
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


        # third deferred, to signal command's output was fully received
        if self.response_required:
            self.response_deferred.callback(self.response)
            # Got response, close connection
            self.close()



    def send_command(self, command):
        """
        Sends a command via Telnet using line mode
        """
        log.debug(f'Sent command {command}')
        self.command = f'{command}\r'
        self.command = command.encode()
        self.sendLine(self.command)
        if not self.response_required:
            self.close()

    def close(self):
        """
        Sends exit to the Telnet server and closes connection.
        Fires the deferred with the command's output.
        """
        #self.sendLine(b'exit')
        self.factory.transport.loseConnection()



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
