from enum import Enum
import json
import logging

log = logging.getLogger(__name__)

class CommandWarning(RuntimeWarning):
    pass

class CommandError(RuntimeError):
    pass

class Operation(Enum):
    """
    Enumeration of all possible command operations for HIL
    """
    NO_OP = 0
    PWR_SUPPLY_CMD = 1
    SERIAL_CMD = 2
    RECOVERY = 3
    RESTART = 4
    WAIT_ON_VAR = 5
    FORCE_LOAD = 6
    BRING_OFFLINE = 7
    POWER_OFF = 8
    ENABLE = 9
    BOOTED_FORCE = 10
    VERSION_CHECK = 12

class Command(object):
    """
    Object representing a command sent to the HIL.
    """

    def __init__(self,
                 json_data='',
                 operation=Operation.NO_OP,
                 options=None,
                 target=''
                 ):
        """
        Create a HIL command.

        :param json_data: JSON data to build command from, or leave blank to pass in options manually.
        :param operation: Must be an enum of type Operation, or a corresponding integer.  Represents type of operation command performs.
        :param options: Command options, usually a dictionary contianing {'value':'', 'command':''} or the like depending on command.
        :param target: Target of command (VCU, or subcomponent of VCU).  Convention is VCU.subcomponent
        """
        if json_data == '':
            assert isinstance(operation, Operation)
            self.operation = operation
            self.options = options
            self.target = target
        else:
            dict = json.loads(json_data)
            self.operation = dict['operation']
            self.options = dict['options']
            self.target = dict['target']

    def __str__(self):
        """
        String representation of command

        :return: String represetation of command
        """
        d = {'operation': self.operation.value, 'options': self.options, 'target': self.target}
        return f'{json.dumps(d)}\n'

