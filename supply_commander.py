import logging

from telnet_client import TelnetClientFactory, TelnetClient

from twisted.protocols.basic import LineReceiver
from twisted.internet import defer, task, threads
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.defer import DeferredQueue
from twisted.conch.telnet import StatefulTelnetProtocol, TelnetTransport
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

log = logging.getLogger('VCUHIL')
log.setLevel(logging.DEBUG)


TIMEOUT = 30.0

class TelnetConnectionError(Exception):
    pass



class SorensenXPF6020DPCommand(object):
    def __init__(self, command, response=True):
        self.connection_deferred = defer.Deferred()

        self.command_deferred = defer.Deferred()

        self.response_required = response

        if response:
            self.response_deferred = defer.Deferred()

        self.transport = None
        self.command = command

    def connect(self, telnet_factory):
        def check_connection_state(transport):
            transport.protocol.connected_deferred = self.connection_deferred
            return transport

        def connection_failed(reason):
            logging.info(f'Connection Failed for reason: {reason}')
            raise TelnetConnectionError(reason)

        # Start connection to telnet server
        self.connection_deferred = endpoint.connect(telnet_factory)

        # first deferred, fired on connection
        self.connection_deferred.addCallback(check_connection_state)
        self.connection_deferred.addErrback(connection_failed)
        self.connection_deferred.addCallback(self.start_protocol)
        self.connection_deferred.addCallback(self.send_command)


    def start_protocol(self, protocol):
        self.transport = protocol.protocol
        self.transport.command_deferred = self.command_deferred
        self.transport.response_required = self.response_required
        if self.response_required:
            self.transport.response_deferred = self.response_deferred

    def send_command(self, _):
        self.transport.send_command(self.command)

    @property
    def response(self):
        if self.response_required:
            return self.response_deferred
        else:
            return None

class SorensenXPF6020DP(object):
    def __init__(self, endpoint):
        self._endpoint = endpoint
        telnet_factory = TelnetClientFactory()
        telnet_factory.protocol = TelnetClient
        self._telnet_factory = telnet_factory

    def _generic_command_response(self, command):
        cmd = SorensenXPF6020DPCommand(command)
        cmd.connect(self._telnet_factory)
        return cmd.response

    def _generic_command(self, command):
        cmd = SorensenXPF6020DPCommand(command, response=False)
        cmd.connect(self._telnet_factory)

    def identify(self):
        return self._generic_command_response('*IDN?')

    @property
    def voltage_channel1(self):
        return self._generic_command_response(f'V1?')

    @voltage_channel1.setter
    def voltage_channel1(self, voltage):
        self._generic_command(f'V1 {float(voltage)}')

    @property
    def voltage_channel2(self):
        return self._generic_command_response(f'V2?')

    @voltage_channel2.setter
    def voltage_channel2(self, voltage):
        self._generic_command(f'V2 {float(voltage)}')

    @property
    def current_channel1(self):
        return self._generic_command_response(f'I1?')

    @current_channel1.setter
    def current_channel1(self, current):
        self._generic_command(f'I1 {float(current)}')

    @property
    def current_channel2(self):
        return self._generic_command_response(f'I2?')

    @current_channel2.setter
    def current_channel2(self, current):
        self._generic_command(f'I2 {float(current)}')

    @property
    def voltage_channel1_meas(self):
        return self._generic_command_response(f'V1O?')

    @property
    def voltage_channel2_meas(self):
        return self._generic_command_response(f'V2O?')

    @property
    def current_channel1_meas(self):
        return self._generic_command_response(f'I1O?')

    @property
    def current_channel2_meas(self):
        return self._generic_command_response(f'I2O?')

    @property
    def output_channel1(self):
        return self._generic_command_response('OP1?')

    @output_channel1.setter
    def output_channel1(self, boolean):
        self._generic_command(f'OP1 {int(boolean)}')

    @property
    def output_channel2(self):
        return self._generic_command_response('OP2?')

    @output_channel2.setter
    def output_channel2(self, boolean):
        self._generic_command(f'OP2 {int(boolean)}')



if __name__ == '__main__':
    logging.basicConfig()

    import sys
    from twisted.internet import reactor

    host = sys.argv[1]
    port = 9221
    endpoint = TCP4ClientEndpoint(reactor, host, port, TIMEOUT)
    psu = SorensenXPF6020DP(endpoint)

    # Identify Power Supply
    idn_r = psu.identify()
    idn_r.addCallback(print)

    # Measure voltages and currents
    v1_r_1 = task.deferLater(reactor, 1, getattr, psu, 'voltage_channel1_meas')
    v2_r_1 = task.deferLater(reactor, 1.2, getattr, psu, 'voltage_channel2_meas')
    i1_r_1 = task.deferLater(reactor, 1.4, getattr, psu, 'current_channel1_meas')
    i2_r_1 = task.deferLater(reactor, 1.6, getattr, psu, 'current_channel2_meas')
    v1_r_1.addCallback(print)
    v2_r_1.addCallback(print)
    i1_r_1.addCallback(print)
    i2_r_1.addCallback(print)

    # Set Voltage, Currents and Outputs
    reactor.callLater(1.8, setattr, psu, 'voltage_channel1', 16.0)
    reactor.callLater(2.0, setattr, psu, 'voltage_channel2', 16.0)
    reactor.callLater(2.2, setattr, psu, 'current_channel1', 7.0)
    reactor.callLater(2.4, setattr, psu, 'current_channel2', 7.0)
    reactor.callLater(2.6, setattr, psu, 'output_channel1', 1)
    reactor.callLater(2.8, setattr, psu, 'output_channel2', 1)

    # Read voltages and currents measured
    v1_r_2 = task.deferLater(reactor, 3, getattr, psu, 'voltage_channel1_meas')
    v2_r_2 = task.deferLater(reactor, 3.2, getattr, psu, 'voltage_channel2_meas')
    i1_r_2 = task.deferLater(reactor, 3.4, getattr, psu, 'current_channel1_meas')
    i2_r_2 = task.deferLater(reactor, 3.6, getattr, psu, 'current_channel2_meas')
    v1_r_2.addCallback(print)
    v2_r_2.addCallback(print)
    i1_r_2.addCallback(print)
    i2_r_2.addCallback(print)

    # Stop reactor after 5 seconds
    reactor.callLater(5, reactor.stop)

    # Execute Script
    reactor.run()