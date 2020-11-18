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
            login_timeout=1
        )

    async def _sga_connect(self):
        return await asyncssh.connect(
            self.host,
            port=self.port,
            username = 'root',
            password='root',
            login_timeout=1
        )

    async def pinger_loop(self):
        logging.debug('Starting HPA Pinger')
        while not self._pinger_stop.is_set():
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                sga_conn = await self._sga_connect()
                conn = await self._connect_through_odb(sga_conn)
                result = await conn.run('echo "Hello!"', check=True)
                conn.close()
                sga_conn.close()
                if result.exit_status == 0:
                    # ping succeeded
                    logging.debug('HPA Available')
                    self._pinger_connected.set()
                else:
                    # ping failed
                    logging.debug('HPA Not Available')
                    self._pinger_connected.clear()
            except gaierror:
                logging.debug('HPA Not Available')
                self._pinger_connected.clear()
            except OSError:
                logging.debug('HPA Not Available')
                self._pinger_connected.clear()

    def is_connected(self):
        return self._pinger_connected.is_set()

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