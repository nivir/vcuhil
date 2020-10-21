# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
import hil_config
import sys, os

from twisted.internet import protocol, defer, endpoints, task
from twisted.conch.endpoints import SSHCommandClientEndpoint

import argparse


# Classes
async def sshtest(reactor, username="alice", sshhost="example.com", portno="22"):
    envAgent = endpoints.UNIXClientEndpoint(reactor, os.environ["SSH_AUTH_SOCK"])
    endpoint = SSHCommandClientEndpoint.newConnection(
        reactor, "echo 'hello world'", username, sshhost,
        int(portno), agentEndpoint=envAgent,
    )

    class ShowOutput(protocol.Protocol):
        received = b""
        def dataReceived(self, data):
            self.received += data
        def connectionLost(self, reason):
            finished.callback(self.received)

    finished = defer.Deferred()
    factory = protocol.Factory.forProtocol(ShowOutput)
    await endpoint.connect(factory)
    print("SSH response:", await finished)


# Main Function
def main(args):
    task.react(lambda *a, **k: defer.ensureDeferred(sshtest(*a, **k)), sys.argv[1:])




# Command Line Interface
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='vcuhil_service',
                                     description='Service to manage VCU HIL on main x86 computer (April).')
    parser.add_argument(
        '--username',
        default='baird.hendrix'
    )
    parser.add_argument(
        '--sshhost',
        default='192.168.1.2'
    )
    parser.add_argument(
        '--portno',
        default=22
    )
    args = parser.parse_args()
    main(vars(args))
