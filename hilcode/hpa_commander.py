import asyncio
import asyncssh
from socket import gaierror
import logging

log = logging.getLogger(__name__)


def _trim_string(string):
        return str(string).strip()


class VCUHPA(object):
    def __init__(self, host, port=22):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect_through_odb(self, sga_connection):
        return await asyncssh.connect(
            self.host,
            port=self.port,
            tunnel=sga_connection,
            username = 'root',
            password='root',
            login_timeout=1
        )

    async def ping_through_odb(self, sga_connection):
        logging.debug('HPA PINGING')
        try:
            conn = await self.connect_through_odb(sga_connection)
            result = await conn.run('echo "Hello!"', check=True)
            conn.close()
            if result.exit_status == 0:
                # ping succeeded
                logging.debug('HPA Available')
                return True
            else:
                # ping failed
                logging.debug('HPA Not Available')
                return False
        except gaierror:
            logging.debug('HPA Not Available')
            return False
        except OSError:
            logging.debug('HPA Not Available')
            return False



