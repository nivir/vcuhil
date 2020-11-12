import asyncio
import telnetlib3
import logging

log = logging.Logger('supply_commander')


def _trim_string(string):
        return str(string).strip()


class SorensenXPF6020DP(object):
    def __init__(self):
        self.reader = None
        self.writer = None

    async def connect(self, host, port):
        logging.debug('CONNECTING')
        coro = telnetlib3.open_connection(host, port)
        self.reader, self.writer = await coro
        logging.debug('CONNECTED')

    async def readback(self):
        return {
            1: {
                'meas_voltage':await self.get_voltage_channel1_meas(),
                'meas_current':await self.get_current_channel1_meas(),
                'set_voltage':await self.get_voltage_channel1(),
                'set_current':await self.get_current_channel1(),
                'output_enabled':await self.get_output_channel1(),
            },
            2: {
                'meas_voltage':await self.get_voltage_channel2_meas(),
                'meas_current':await self.get_current_channel2_meas(),
                'set_voltage':await self.get_voltage_channel2(),
                'set_current':await self.get_current_channel2(),
                'output_enabled':await self.get_output_channel2(),
            }
        }

    def close(self):
        self.writer.close()

    async def _generic_command_response(self, command):
        logging.debug(f'WRITING: {command}')
        self.writer.write(command)
        response = await self.reader.readline()
        logging.debug(f'RECV: {response}')
        return _trim_string(response)

    def _generic_command(self, command):
        logging.debug(f'WRITING: {command}')
        self.writer.write(command)

    async def identify(self):
        return await self._generic_command_response('*IDN?')

    async def get_voltage_channel1(self):
        return float((await self._generic_command_response(f'V1?'))[3:])

    def set_voltage_channel1(self, voltage):
        self._generic_command(f'V1 {float(voltage)}')

    async def get_voltage_channel2(self):
        return float((await self._generic_command_response(f'V2?'))[3:])

    def set_voltage_channel2(self, voltage):
        self._generic_command(f'V2 {float(voltage)}')

    async def get_current_channel1(self):
        return float((await self._generic_command_response(f'I1?'))[3:])

    def set_current_channel1(self, current):
        self._generic_command(f'I1 {float(current)}')

    async def get_current_channel2(self):
        return float((await self._generic_command_response(f'I2?'))[3:])

    def set_current_channel2(self, current):
        self._generic_command(f'I2 {float(current)}')

    async def get_voltage_channel1_meas(self):
        return float((await self._generic_command_response(f'V1O?'))[:-1])

    async def get_voltage_channel2_meas(self):
        return float((await self._generic_command_response(f'V2O?'))[:-1])

    async def get_current_channel1_meas(self):
        return float((await self._generic_command_response(f'I1O?'))[:-1])

    async def get_current_channel2_meas(self):
        return float((await self._generic_command_response(f'I2O?'))[:-1])

    async def get_output_channel1(self):
        return bool((await self._generic_command_response('OP1?'))[:])

    def set_output_channel1(self, boolean):
        self._generic_command(f'OP1 {int(boolean)}')

    async def get_output_channel2(self):
        return bool((await self._generic_command_response('OP2?'))[:])

    def set_output_channel2(self, boolean):
        self._generic_command(f'OP2 {int(boolean)}')

    async def supply_state(self):
        logging.debug('Get Supply State')
        return await self.readback()

async def main():
    # Setup
    psu = SorensenXPF6020DP()

    await psu.connect('psu-leonardo', 9221)

    idn = await psu.identify()
    print(idn)
    print((await psu.supply_state()))
    await asyncio.sleep(1)
    psu.set_voltage_channel1(16.0)
    psu.set_voltage_channel2(16.0)
    psu.set_current_channel1(7.0)
    psu.set_current_channel2(7.0)
    psu.set_output_channel1(1)
    psu.set_output_channel2(1)

    await asyncio.sleep(1)
    print((await psu.supply_state()))

    await asyncio.sleep(1)
    psu.set_voltage_channel1(0)
    psu.set_voltage_channel2(0)
    psu.set_current_channel1(0)
    psu.set_current_channel2(0)
    psu.set_output_channel1(0)
    psu.set_output_channel2(0)

    await asyncio.sleep(1)
    psu.close()



if __name__ == '__main__':
    asyncio.run(main())

