import asyncio
import asyncssh
import logging

log = logging.getLogger(__name__)

PINGER_CYCLE_TIME = 0.5

class VCUHPA(object):
    def __init__(self, sga_host, hpa_host, sga_port=22, port=22):
        self.sga_host = sga_host
        self.sga_port = sga_port
        self.host = hpa_host
        self.port = port
        self._pinger_task = None
        self._pinger_connected = asyncio.Event()
        self._pinger_stop = asyncio.Event()

    async def pinger_loop(self):
        while not self._pinger_stop.is_set():
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                async with await asyncio.wait_for(asyncssh.connect(
                    self.sga_host,
                    port=self.sga_port,
                    username = 'root',
                    password='root',
                    login_timeout=10,
                ), timeout=10) as sga_conn:
                    async with await asyncio.wait_for(asyncssh.connect(
                        self.host,
                        port=self.port,
                        tunnel=sga_conn,
                        username = 'root',
                        password='root',
                        login_timeout=10,
                    ), timeout=10) as conn:
                        result = await asyncio.wait_for(conn.run('echo "Test"', check=True), timeout=10)
                if result.exit_status == 0:
                    # ping succeeded
                    self._pinger_connected.set()
                else:
                    # ping failed
                    self._pinger_connected.clear()
            except Exception:
                self._pinger_connected.clear()

    def is_connected(self):
        return self._pinger_connected.is_set()

    async def setup(self):
        self._pinger_stop.clear()
        self._pinger_connected.clear()
        self._pinger_task = asyncio.create_task(self.pinger_loop())

    async def close(self):
        log.debug('closing hpa')
        self._pinger_stop.set()
        while not self._pinger_task.done():
            await asyncio.sleep(0.1)
        log.debug('closed hpa')