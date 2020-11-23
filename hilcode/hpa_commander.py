import asyncio
import asyncssh
import logging

log = logging.getLogger(__name__)

PINGER_CYCLE_TIME = 0.5

class VCUHPA(object):
    """
    Interface library for talking with HPA
    """

    def __init__(self, sga_host, hpa_host, sga_port=22, port=22):
        """
        VCUHPA Interface object

        :param sga_host: SGA Hostname/IP (assumes on same VLAN)
        :param hpa_host: HPA Hostname/IP (from SGA)
        :param sga_port: SGA SSH Port (default is 22)
        :param port: HPA SSH Port (default is 22)
        """
        self.sga_host = sga_host
        self.sga_port = sga_port
        self.host = hpa_host
        self.port = port
        self._pinger_task = None
        self._pinger_connected = asyncio.Event()
        self._pinger_stop = asyncio.Event()
        self._pinger_version_uname = asyncio.Queue(1)
        self._pinger_version_nvidia = asyncio.Queue(1)


    async def pinger_loop(self):
        """
        Coroutine that implements the pinger and version checker.
        """
        while not self._pinger_stop.is_set():
            await asyncio.sleep(PINGER_CYCLE_TIME)
            try:
                async with await asyncio.wait_for(asyncssh.connect(
                    self.sga_host,
                    port=self.sga_port,
                    username = 'root',
                    password='root',
                    preferred_auth='password',
                    login_timeout=10,
                ), timeout=10) as sga_conn:
                    async with await asyncio.wait_for(asyncssh.connect(
                        self.host,
                        port=self.port,
                        tunnel=sga_conn,
                        username = 'root',
                        password='root',
                        preferred_auth='password',
                        login_timeout=10,
                    ), timeout=10) as conn:
                        uname_result = await asyncio.wait_for(conn.run(
                            'uname -a', check=True), timeout=10)
                        nvidia_result = await asyncio.wait_for(conn.run(
                            'cat /usr/libnvidia/version-pdk.txt', check=True), timeout=10)
                if uname_result.exit_status == 0 and nvidia_result.exit_status == 0:
                    # ping succeeded
                    self._pinger_connected.set()
                    if self._pinger_version_uname.full():
                        self._pinger_version_uname.get_nowait()
                    await self._pinger_version_uname.put(uname_result.stdout)
                    if self._pinger_version_nvidia.full():
                        self._pinger_version_nvidia.get_nowait()
                    await self._pinger_version_uname.put(nvidia_result.stdout)
                else:
                    # ping failed
                    self._pinger_connected.clear()
            except asyncio.exceptions.TimeoutError:
                self._pinger_connected.clear()
            except OSError:
                self._pinger_connected.clear()
            except Exception as e:
                log.error(f'WTF HPA ERROR!!! {e}')
                raise e

    def is_connected(self):
        """
        Is the HPA currently connected?

        :return: True/False if HPA is connected
        """
        return self._pinger_connected.is_set()

    def uname_version(self):
        """
        What version from the HPA is given when running 'uname -a'?

        :return: String showing return of 'uname -a' from HPA
        """
        try:
            return self._pinger_version_uname.get_nowait()
        except asyncio.QueueEmpty:
            return 'not_connected'

    def nvidia_version(self):
        """
        What version from the HPA is given with the output of 'cat /usr/libnvidia/version-pdk.txt'?

        :return: String showing return of 'cat /usr/libnvidia/version-pdk.txt' from HPA
        """
        try:
            return self._pinger_version_nvidia.get_nowait()
        except asyncio.QueueEmpty:
            return 'not_connected'

    async def setup(self):
        """
        Setup of VCU HPA (starts pinger and version checker)
        """
        self._pinger_stop.clear()
        self._pinger_connected.clear()
        self._pinger_task = asyncio.create_task(self.pinger_loop())

    async def close(self):
        """
        Close VCU HPA (stop pinger and version checker)
        """
        self._pinger_stop.set()
        while not self._pinger_task.done():
            await asyncio.sleep(0.1)