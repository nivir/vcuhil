import asyncio
import asyncssh
from socket import gaierror
import logging

log = logging.getLogger(__name__)


def _trim_string(string):
        return str(string).strip()


class VCUSGA(object):
    def __init__(self, host, port=22):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def ping(self):
        logging.debug('SGA PINGING')
        try:
            async with asyncssh.connect(self.host, port=self.port, username = 'root', password='root', login_timeout=1) as conn:
                result = await conn.run('echo "Hello!"', check=True)
                conn.close()
                if result.exit_status == 0:
                    # ping succeeded
                    logging.debug('SGA Available')
                    return True
                else:
                    # ping failed
                    logging.debug('SGA Not Available')
                    return False
        except gaierror:
            logging.debug('SGA Not Available')
            return False
        except OSError:
            logging.debug('SGA Not Available')
            return False


    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def command(self, command):
        logging.debug(f'WRITING: {command}')
        self.writer.write(f'{command}\n'.encode())
        await asyncio.sleep(0.1)



