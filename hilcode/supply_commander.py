import asyncio
import telnetlib3
import logging

log = logging.getLogger(__name__)


def _trim_string(string):
        return str(string).strip()


class SorensenXPF6020DP(object):
    def __init__(self):
        self.reader = None
        self.writer = None
        self.closed = True

    async def _on_connection(self):
        await self._generic_command('*CLS')

    async def connect(self, host, port):
        self.reader, self.writer = await telnetlib3.open_connection(host, port)
        self.closed = False
        await self._on_connection()
        log.debug('CONNECTED')

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

    async def close(self):
        self.writer.close()
        self.closed = True

    async def _generic_command_response(self, command):
        if not self.closed:
            log.debug(f'WRITING: {command}')
            self.writer.write(command)
            await self.writer.drain()
            response = await self.reader.readline()
            log.debug(f'RECV: {response}')
            return _trim_string(response)
        else:
            raise RuntimeError('THIS IS SUPPOSED TO BE CLOSED')

    async def _generic_command(self, command):
        if not self.closed:
            log.debug(f'WRITING: {command}')
            self.writer.write(command)
            await self.writer.drain()
        else:
            raise RuntimeError('THIS IS SUPPOSED TO BE CLOSED')

    async def identify(self):
        return await self._generic_command_response('*IDN?')

    async def get_voltage_channel1(self):
        return float((await self._generic_command_response(f'V1?'))[3:])

    async def set_voltage_channel1(self, voltage):
        await self._generic_command(f'V1 {float(voltage)}')

    async def get_voltage_channel2(self):
        return float((await self._generic_command_response(f'V2?'))[3:])

    async def set_voltage_channel2(self, voltage):
        await self._generic_command(f'V2 {float(voltage)}')

    async def get_current_channel1(self):
        return float((await self._generic_command_response(f'I1?'))[3:])

    async def set_current_channel1(self, current):
        await self._generic_command(f'I1 {float(current)}')

    async def get_current_channel2(self):
        return float((await self._generic_command_response(f'I2?'))[3:])

    async def set_current_channel2(self, current):
        await self._generic_command(f'I2 {float(current)}')

    async def get_voltage_channel1_meas(self):
        return float((await self._generic_command_response(f'V1O?'))[:-1])

    async def get_voltage_channel2_meas(self):
        return float((await self._generic_command_response(f'V2O?'))[:-1])

    async def get_current_channel1_meas(self):
        return float((await self._generic_command_response(f'I1O?'))[:-1])

    async def get_current_channel2_meas(self):
        return float((await self._generic_command_response(f'I2O?'))[:-1])

    async def get_output_channel1(self):
        return int((await self._generic_command_response('OP1?'))[:])

    async def set_output_channel1(self, boolean):
        await self._generic_command(f'OP1 {int(boolean)}')

    async def get_output_channel2(self):
        return int((await self._generic_command_response('OP2?'))[:])

    async def set_output_channel2(self, boolean):
        await self._generic_command(f'OP2 {int(boolean)}')

    async def supply_state(self):
        log.debug('Get Supply State')
        return await self.readback()

async def main():
    # Setup
    psu = SorensenXPF6020DP()

    await psu.connect('psu-leonardo', 9221)

    idn = await psu.identify()
    print(idn)
    print((await psu.supply_state()))
    await asyncio.sleep(1)
    await psu.set_voltage_channel1(16.0)
    await psu.set_voltage_channel2(16.0)
    await psu.set_current_channel1(7.0)
    await psu.set_current_channel2(7.0)
    await psu.set_output_channel1(1)
    await psu.set_output_channel2(1)

    await asyncio.sleep(1)
    print((await psu.supply_state()))

    await asyncio.sleep(1)
    await psu.set_voltage_channel1(0)
    await psu.set_voltage_channel2(0)
    await psu.set_current_channel1(0)
    await psu.set_current_channel2(0)
    await psu.set_output_channel1(0)
    await psu.set_output_channel2(0)

    await asyncio.sleep(1)
    await psu.close()



if __name__ == '__main__':
    asyncio.run(main())

