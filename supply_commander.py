import logging

from telnet_client import TelnetClientFactory

from twisted.protocols.basic import LineReceiver
from twisted.internet import defer, task, threads
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.conch.telnet import StatefulTelnetProtocol, TelnetTransport
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

log = logging.getLogger('VCUHIL')
log.setLevel(logging.DEBUG)


TIMEOUT = 30.0

class TelnetConnectionError(Exception):
    pass



class SorensenXPF6020DPCommand(object):
    def __init__(self, command):
        self.connection_deferred = defer.Deferred()

        self.command_deferred = defer.Deferred()
        self.command_deferred.addCallback(self.received_response)

        self.transport = None
        self.command = command

    def connect(self, host, port):
        def check_connection_state(transport):
            transport.protocol.connected_deferred = self.connection_deferred
            return transport

        def connection_failed(reason):
            logging.info(f'Connection Failed for reason: {reason}')
            raise TelnetConnectionError(reason)

        # Start connection to telnet server
        endpoint = TCP4ClientEndpoint(reactor, host, port, TIMEOUT)
        telnet_factory = TelnetClientFactory()
        telnet_factory.protocol = StatefulTelnetProtocol
        self.connection_deferred = endpoint.connect(telnet_factory)

        # first deferred, fired on connection
        self.connection_deferred.addCallback(check_connection_state)
        self.connection_deferred.addErrback(connection_failed)
        self.connection_deferred.addCallback(self.start_protocol)
        self.connection_deferred.addCallback(self.send_command)

    def start_protocol(self, protocol):
        self.transport = protocol.protocol
        self.transport.command_deferred = self.command_deferred

    def send_command(self, _):
        self.transport.send_command(self.command)

    def received_response(self, _):
        print(_)



if __name__ == '__main__':
    logging.basicConfig()

    import sys
    from twisted.internet import reactor

    host = sys.argv[1]
    port = 9221
    SorensenXPF6020DPCommand('*IDN?').connect(host, port)
    reactor.run()