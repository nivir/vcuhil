import asyncio
import telnetlib3
import logging

log = logging.getLogger(__name__)

CYCLE_TIME = 0.1

def _trim_string(string):
        return str(string).strip()


class SorensenXPF6020DP(object):
    """
    Abstraction layer for interfacing with Sorensen XPF 60-20DP Power Supplies
    """

    def __init__(self):
        """
        Abstraction layer for Sorensen XPF 60-20DP Power Supply
        """
        self._comm_loop_exit = asyncio.Event()
        self._new_telem = asyncio.Event()
        self._comm_telem_queue = asyncio.Queue()
        self._comm_cmd_queue = asyncio.Queue()
        self._comm_task = None

    async def _on_connection(self):
        """
        Convenience function of things to run on connection with supply.
        """
        await self._generic_command('*RST')

    async def connect(self, host, port=9221):
        """
        Connect to Sorensen XPF 60-20DP

        :param host: Hostname/IP of Supply
        :param port: Port of Supply (default is 9221)
        """
        self._comm_task = asyncio.create_task(self._comm_loop(host, port))
        await self._on_connection()
        log.debug('CONNECTED')

    async def _comm_loop(self, host, port=9221):
        """
        Coroutine that facilitates communication with power supply.

        :param host: Supply hostname/IP
        :param port: Supply port (default is 9221)
        """
        # Connect to power supply
        reader, writer = await telnetlib3.open_connection(host, port)
        while not self._comm_loop_exit.is_set():
            # Get Telemetry
            if not self._new_telem.is_set():
                await self._comm_telem_queue.put(await self._telem_readback(reader, writer))
                self._new_telem.set() # Flag that new telemetry is available
            # Send Commands
            while not self._comm_cmd_queue.empty():
                await self._generic_command_loop(writer, await self._comm_cmd_queue.get())
            await asyncio.sleep(CYCLE_TIME)
        writer.close()

    async def _generic_command_loop(self, writer, command):
        """
        Sends a generic command from the communications loop

        :param writer: Writer object to write command to
        :param command: Command to send
        """
        log.debug(f'WRITING: {command}')
        writer.write(command)
        await writer.drain()

    async def _telem_readback(self, reader, writer):
        """
        Gets telemetry information from supply.

        :param reader: Reader stream to get information from
        :param writer: Writer stream to push information to
        """
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
        """
        Convenience function to gather telemetry data from power supply.

        :param reader: Reader stream for supply
        :param writer: Writer stream for supply
        :param command: Command to send supply
        :return: Response to command
        """
        log.debug(f'WRITING: {command}')
        writer.write(command)
        await writer.drain()
        response = await reader.readline()
        log.debug(f'RECV: {response}')
        return _trim_string(response)

    async def readback(self):
        """
        Get latest telemetry data from supply.

        :return: Telemetry data
        """

    async def close(self):
        """
        Close power supply communications
        """
        self._comm_loop_exit.set()
        while not self._comm_task.done():
            await asyncio.sleep(0.1)

    async def _generic_command(self, command):
        """
        Send a command to the supply.

        :param command: Command to send
        """
        await self._comm_cmd_queue.put(command)

    async def set_voltage_channel1(self, voltage):
        """
        Set Channel 1 Voltage Setpoint

        :param voltage: Voltage setpoint
        """
        await self._generic_command(f'V1 {float(voltage)}')

    async def set_voltage_channel2(self, voltage):
        """
        Set Channel 2 Voltage Setpoint

        :param voltage: Voltage setpoint
        """
        await self._generic_command(f'V2 {float(voltage)}')

    async def set_current_channel1(self, current):
        """
        Set Channel 1 Current Setpoint

        :param current: Current setpoint
        """
        await self._generic_command(f'I1 {float(current)}')

    async def set_current_channel2(self, current):
        """
        Set Channel 2 Current Setpoint

        :param current: Current setpoint
        """
        await self._generic_command(f'I2 {float(current)}')

    async def set_output_channel1(self, boolean):
        """
        Set Channel 1 Output Enable

        :param boolean: Output Enable
        """
        await self._generic_command(f'OP1 {int(boolean)}')

    async def set_output_channel2(self, boolean):
        """
        Set Channel 1 Output Enable

        :param boolean: Output Enable
        """
        await self._generic_command(f'OP2 {int(boolean)}')

    async def supply_state(self):
        """
        Get state of power supply.
        """
        log.debug('Get Supply State')
        # Tell loop to acquire new telemetry
        self._new_telem.clear()
        # Return telemetry from queue
        return await self._comm_telem_queue.get()
