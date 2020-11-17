import asyncio
import pprint
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
        logging.debug('CONNECTING to serial device')
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=serial, baudrate=baudrate)
        logging.debug('CONNECTED to serial device')

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def flush_buffer(self):
        data = []
        try:
            while True:
                data.append(await asyncio.wait_for(self.reader.readline(), timeout=0.1))
        except asyncio.TimeoutError:
            log.debug('buffer flushed')
        return data

    async def command(self, command):
        logging.info(await self.flush_buffer())
        self.writer.write('\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)
        logging.info(await self.flush_buffer()) # SB Prompt
        cmd = command['command']
        log.debug(f'WRITING: {cmd}')
        self.writer.write(f'{cmd}\r\n'.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)



