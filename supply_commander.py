import telnetlib
import logging
import pprint

log = logging.Logger('VCUHIL')
log.setLevel('DEBUG')

def _trim_string(string):
        return str(string).split('\\r\\n')[0]


class SorensenXPF6020DP(object):
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self.psu_tel = None

    def connect(self):
        self.psu_tel = telnetlib.Telnet('psu-leonardo', 9221)

    def readback(self):
        return {
            1: {
                'meas_voltage':self.voltage_channel1_meas,
                'meas_current':self.current_channel1_meas,
                'set_voltage':self.voltage_channel1,
                'set_current':self.current_channel1,
                'output_enabled':self.output_channel1,
            },
            2: {
                'meas_voltage':self.voltage_channel2_meas,
                'meas_current':self.current_channel2_meas,
                'set_voltage':self.voltage_channel2,
                'set_current':self.current_channel2,
                'output_enabled':self.output_channel2,
            }
        }

    def close(self):
        self.psu_tel.close()

    def _generic_command_response(self, command):
        self._generic_command(command)
        response = self.psu_tel.read_until(b'\r\n')
        return _trim_string(response)

    def _generic_command(self, command):
        self.psu_tel.write(f'{command}\r\n'.encode('ascii'))

    def identify(self):
        return self._generic_command_response('*IDN?')[2:]

    @property
    def voltage_channel1(self):
        return float(self._generic_command_response(f'V1?')[5:])

    @voltage_channel1.setter
    def voltage_channel1(self, voltage):
        self._generic_command(f'V1 {float(voltage)}')

    @property
    def voltage_channel2(self):
        return float(self._generic_command_response(f'V2?')[5:])

    @voltage_channel2.setter
    def voltage_channel2(self, voltage):
        self._generic_command(f'V2 {float(voltage)}')

    @property
    def current_channel1(self):
        return float(self._generic_command_response(f'I1?')[5:])

    @current_channel1.setter
    def current_channel1(self, current):
        self._generic_command(f'I1 {float(current)}')

    @property
    def current_channel2(self):
        return float(self._generic_command_response(f'I2?')[5:])

    @current_channel2.setter
    def current_channel2(self, current):
        self._generic_command(f'I2 {float(current)}')

    @property
    def voltage_channel1_meas(self):
        return float(self._generic_command_response(f'V1O?')[2:-1])

    @property
    def voltage_channel2_meas(self):
        return float(self._generic_command_response(f'V2O?')[2:-1])

    @property
    def current_channel1_meas(self):
        return float(self._generic_command_response(f'I1O?')[2:-1])

    @property
    def current_channel2_meas(self):
        return float(self._generic_command_response(f'I2O?')[2:-1])

    @property
    def output_channel1(self):
        return bool(self._generic_command_response('OP1?')[2:])

    @output_channel1.setter
    def output_channel1(self, boolean):
        self._generic_command(f'OP1 {int(boolean)}')

    @property
    def output_channel2(self):
        return bool(self._generic_command_response('OP2?')[2:])

    @output_channel2.setter
    def output_channel2(self, boolean):
        self._generic_command(f'OP2 {int(boolean)}')

    def supply_state(self):
        return pprint.pformat(self.readback())


if __name__ == '__main__':
    import time
    psu = SorensenXPF6020DP('psu-leonardo', 9221)
    psu.connect()
    print(psu.identify())
    print(psu.supply_state())
    time.sleep(0.5)
    psu.voltage_channel1 = 16.0
    psu.voltage_channel2 = 16.0
    psu.current_channel1 = 7.0
    psu.current_channel2 = 7.0
    psu.output_channel1 = 1
    psu.output_channel2 = 1
    time.sleep(1.5)
    print(psu.supply_state())
    time.sleep(2)
    psu.voltage_channel1 = 0
    psu.voltage_channel2 = 0
    psu.current_channel1 = 0
    psu.current_channel2 = 0
    psu.output_channel1 = 0
    psu.output_channel2 = 0
    time.sleep(0.5)
    psu.close()

