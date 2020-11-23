import asyncio
import time
import serial_asyncio
import logging

log = logging.getLogger(__name__)


class SerialLine(object):
    """
    Convenience object for timestamping serial data line-by-line
    """
    def __init__(self, timestamp, data):
        """
        Creates an object containing a line of serial data and a timestamp.

        :param timestamp: Timestamp of serial line
        :param data: Serial line
        """
        self.time = timestamp
        self.data = str(data)

    def __str__(self):
        """
        Outputs serial line with timestamp

        :return: Timestamp and serial line, in same string.
        """
        return f'{self.time}: {self.data}'

def _trim_string(string):
    """
    Convenience function for removing whitespace from strings, nice place to change how strings are processed.

    :param string: String to strip
    :return: Stripped string
    """
    return str(string).strip()


class VCUSerialDevice(object):
    """
    Abstraction layer for VCU Serial Device
    """

    def __init__(self):
        """
        Create VCU Serial Device
        """
        self.reader = None
        self.writer = None
        self.line_reader_queue = asyncio.Queue()
        self.line_reader_exit = asyncio.Event()
        self._line_reader_task = None

    async def start(self):
        """
        Start vehicle task
        """
        self._line_reader_task = asyncio.create_task(self.line_reader())

    async def connect(self, serial, baudrate=115200):
        """
        Connect to serial port

        :param serial: Serial port URL (typically '/dev/ttyUSB0' or the like)
        :param baudrate: Baud rate of serial port (default is 115200 baud)
        """
        logging.info(f'CONNECTING to serial device {serial} at baud rate {baudrate}')
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=serial, baudrate=baudrate)
        logging.debug('CONNECTED to serial device')

    async def close(self):
        """
        Close serial port
        """
        self.line_reader_exit.set()
        while not self._line_reader_task.done():
            await asyncio.sleep(0.1)
        self.writer.close()
        await self.writer.wait_closed()

    async def line_reader(self):
        """
        Coroutine that runs in background, timestamps incoming serial lines, and places in queue.
        """
        while not self.line_reader_exit.is_set():
            try:
                await self.line_reader_queue.put(
                    SerialLine(
                        time.time(),
                        await asyncio.wait_for(self.reader.readline(), timeout=0.1)
                    )
                )
            except asyncio.TimeoutError:
                # Buffer is clear
                pass
            except Exception as e:
                log.error('WTF!!!!')
                raise e

    def get_line_nowait(self):
        """
        Get latest serial line from queue.

        :return: Latest serial line, or a asyncio.QueueEmpty exception
        """
        return self.line_reader_queue.get_nowait()

    def line_available(self):
        """
        Is there a new serial line available?

        :return: True/False if new serial line available
        """
        return not self.line_reader_queue.empty()

    async def command(self, command):
        """
        Send a command out the serial port

        :param command: Command to send
        """
        self.writer.write('\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)
        cmd = command['command']
        log.debug(f'WRITING: {cmd}')
        self.writer.write(f'{cmd}\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)



