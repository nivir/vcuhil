import asyncio
import time
import serial_asyncio
import logging

log = logging.getLogger(__name__)


class SerialLine(object):
    def __init__(self, timestamp, data):
        self.time = timestamp
        self.data = str(data)

    def __str__(self):
        return f'{self.time}: {self.data}'

def _trim_string(string):
        return str(string).strip()


class VCUMicroDevice(object):
    def __init__(self):
        self.reader = None
        self.writer = None
        self.line_reader_queue = asyncio.Queue()
        self.line_reader_exit = asyncio.Event()
        self._line_reader_task = None

    async def start(self):
        self._line_reader_task = asyncio.create_task(self.line_reader())

    async def connect(self, serial, baudrate=115200):
        logging.debug('CONNECTING to serial device')
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=serial, baudrate=baudrate)
        logging.debug('CONNECTED to serial device')

    async def close(self):
        self._line_reader_exit.set()
        while not self._line_reader_task.done():
            await asyncio.sleep(0.1)
        self.writer.close()
        await self.writer.wait_closed()

    async def line_reader(self):
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
                await asyncio.sleep(0.1)

    def get_line_nowait(self):
        return self.line_reader_queue.get_nowait()

    def line_available(self):
        return not self.line_reader_queue.empty()

    async def command(self, command):
        self.writer.write('\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)
        cmd = command['command']
        log.debug(f'WRITING: {cmd}')
        self.writer.write(f'{cmd}\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)



