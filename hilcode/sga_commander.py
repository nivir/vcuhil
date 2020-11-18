import asyncio
import asyncssh
from socket import gaierror
import logging

log = logging.getLogger(__name__)

PINGER_CYCLE_TIME = 0.5

class VCUSGA(object):
    def __init__(self, host, port=22):
        self.host = host
        self.port = port
        self._pinger_task = None
        self._pinger_connected = asyncio.Event()
        self._pinger_stop = asyncio.Event()

    def is_connected(self):
        return self._pinger_connected.is_set()

    async def pinger_loop(self):
        logging.debug('Starting SGA Pinger')
        while not self._pinger_stop.is_set():
            logging.info('SGA PING')
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                async with await self._connect() as conn:
                    result = await conn.run('echo "Hello!"', check=True)
                if result.exit_status == 0:
                    # ping succeeded
                    logging.info('SGA Available')
                    self._pinger_connected.set()
                else:
                    # ping failed
                    logging.debug('SGA Not Available')
                    self._pinger_connected.clear()
            except Exception:
                logging.debug('SGA Not Available')
                self._pinger_connected.clear()
        logging.info('SGA PING QUIT')


    async def setup(self):
        self._pinger_stop.clear()
        self._pinger_connected.clear()
        self._pinger_task = asyncio.create_task(self.pinger_loop())

    async def close(self):
        self._pinger_stop.set()
        while not self._pinger_task.done():
            await asyncio.sleep(0.1)

    async def _connect(self):
        return await asyncssh.connect(
            self.host,
            port=self.port,
            username = 'root',
            password='root'
        )





