import asyncio
import asyncssh
from socket import gaierror
import logging

log = logging.getLogger(__name__)

PINGER_CYCLE_TIME = 0.5

class VCUHPA(object):
    def __init__(self, sga_host, host, sga_port=22, port=22):
        self.sga_host = sga_host
        self.sga_port = sga_port
        self.host = host
        self.port = port
        self._pinger_task = None
        self._pinger_connected = asyncio.Event()
        self._pinger_stop = asyncio.Event()

    async def _connect_through_odb(self, sga_connection):
        return await asyncssh.connect(
            self.host,
            port=self.port,
            tunnel=sga_connection,
            username = 'root',
            password='root',
        )

    async def _sga_connect(self):
        return await asyncssh.connect(
            self.sga_host,
            port=self.sga_port,
            username = 'root',
            password='root',
        )

    async def pinger_loop(self):
        logging.debug('Starting HPA Pinger')
        while not self._pinger_stop.is_set():
            logging.info('HPA PING')
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                async with await self._sga_connect() as sga_conn:
                    async with await self._connect_through_odb(sga_conn) as conn:
                        result = await conn.run('echo "Hello!"', check=True)
                if result.exit_status == 0:
                    # ping succeeded
                    logging.info('HPA Available')
                    self._pinger_connected.set()
                else:
                    # ping failed
                    logging.debug('HPA Not Available')
                    self._pinger_connected.clear()
            except Exception:
                logging.debug('HPA Not Available')
                self._pinger_connected.clear()
        logging.info('HPA PING QUIT')

    def is_connected(self):
        return self._pinger_connected.is_set()

    async def setup(self):
        self._pinger_stop.clear()
        self._pinger_connected.clear()
        self._pinger_task = asyncio.create_task(self.pinger_loop())

    async def close(self):
        self._pinger_stop.set()
        while not self._pinger_task.done():
            await asyncio.sleep(0.1)
