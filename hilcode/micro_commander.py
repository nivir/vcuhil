import asyncio
import serial_asyncio
import logging

log = logging.getLogger(__name__)


def _trim_string(string):
        return str(string).strip()


class VCUMicroDevice(object):
    def __init__(self):
        self.reader = None
        self.writer = None

    async def connect(self, serial, baudrate=115200):
        logging.debug('CONNECTING')
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=serial, baudrate=baudrate)
        logging.debug('CONNECTED')

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def command(self, command):
        logging.debug(f'WRITING: {command}')
        self.writer.write(f'{command}\n'.encode())
        await asyncio.sleep(0.1)



