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
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                conn = await self._connect()
                result = await conn.run('echo "Hello!"', check=True)
                conn.close()
                if result.exit_status == 0:
                    # ping succeeded
                    logging.debug('SGA Available')
                    self._pinger_connected.set()
                else:
                    # ping failed
                    logging.debug('SGA Not Available')
                    self._pinger_connected.clear()
            except gaierror:
                logging.debug('SGA Not Available')
                self._pinger_connected.clear()
            except OSError:
                logging.debug('SGA Not Available')
                self._pinger_connected.clear()


    async def setup(self):
        self._pinger_task = asyncio.create_task(self.pinger_loop())

    def close(self):
        self._pinger_stop.set()

    async def _connect(self):
        return await asyncssh.connect(
            self.host,
            port=self.port,
            username = 'root',
            password='root',
            login_timeout=1
        )





