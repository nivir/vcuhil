import asyncio
import telnetlib3
import logging

log = logging.getLogger(__name__)

CYCLE_TIME = 0.1

def _trim_string(string):
        return str(string).strip()


class SorensenXPF6020DP(object):
    def __init__(self):
        self._comm_loop_exit = asyncio.Event()
        self._new_telem = asyncio.Event()
        self._comm_telem_queue = asyncio.Queue()
        self._comm_cmd_queue = asyncio.Queue()
        self._comm_loop = None

    async def _on_connection(self):
        await self._generic_command('*RST')

    async def connect(self, host, port):
        self._comm_loop = asyncio.create_task(self.comm_loop(host, port))
        await self._on_connection()
        log.debug('CONNECTED')

    async def comm_loop(self, host, port):
        # Connect to power supply
        reader, writer = await telnetlib3.open_connection(host, port)
        while not self._comm_loop_exit.is_set():
            # Get Telemetry
            if not self._new_telem.is_set():
                await self._comm_telem_queue.put(await self.telem_readback(reader, writer))
                self._new_telem.set() # Flag that new telemetry is available
            # Send Commands
            while not self._comm_cmd_queue.empty():
                await self._generic_command_loop(writer, await self._comm_cmd_queue.get())
            await asyncio.sleep(CYCLE_TIME)
        writer.close()

    async def _generic_command_loop(self, writer, command):
        log.debug(f'WRITING: {command}')
        writer.write(command)
        await writer.drain()

    async def telem_readback(self, reader, writer):
        return {
            0: {
                'idn':await self._telem_response(reader, writer, '*IDN?'),
            },
            1: {
                'meas_voltage':float((await self._telem_response(reader, writer, f'V1O?'))[:-1]),
                'meas_current':float((await self._telem_response(reader, writer, f'I1O?'))[:-1]),
                'set_voltage':float((await self._telem_response(reader, writer, f'V1?'))[3:]),
                'set_current':float((await self._telem_response(reader, writer, f'I1?'))[3:]),
                'output_enabled':int((await self._telem_response(reader, writer, 'OP1?'))[:]),
            },
            2: {
                'meas_voltage':float((await self._telem_response(reader, writer, f'V2O?'))[:-1]),
                'meas_current':float((await self._telem_response(reader, writer, f'I2O?'))[:-1]),
                'set_voltage':float((await self._telem_response(reader, writer, f'V2?'))[3:]),
                'set_current':float((await self._telem_response(reader, writer, f'I2?'))[3:]),
                'output_enabled':int((await self._telem_response(reader, writer, 'OP2?'))[:]),
            }
        }


    async def _telem_response(self, reader, writer, command):
        log.debug(f'WRITING: {command}')
        writer.write(command)
        await writer.drain()
        response = await reader.readline()
        log.debug(f'RECV: {response}')
        return _trim_string(response)

    async def readback(self):
        # Tell loop to acquire new telemetry
        self._new_telem.clear()
        # Return telemetry from queue
        return await self._comm_telem_queue.get()

    async def close(self):
        self._comm_loop_exit.set()
        while not self._comm_loop.done():
            await asyncio.sleep(0.1)

    async def _generic_command(self, command):
        await self._comm_cmd_queue.put(command)

    async def set_voltage_channel1(self, voltage):
        await self._generic_command(f'V1 {float(voltage)}')

    async def set_voltage_channel2(self, voltage):
        await self._generic_command(f'V2 {float(voltage)}')

    async def set_current_channel1(self, current):
        await self._generic_command(f'I1 {float(current)}')

    async def set_current_channel2(self, current):
        await self._generic_command(f'I2 {float(current)}')

    async def set_output_channel1(self, boolean):
        await self._generic_command(f'OP1 {int(boolean)}')

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

