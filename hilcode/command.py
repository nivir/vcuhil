from enum import Enum
import json
import logging

log = logging.getLogger(__name__)

class CommandWarning(RuntimeWarning):
    pass

class CommandError(RuntimeError):
    pass

class Operation(Enum):
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

async def execute_command(state, curr_command):
    if curr_command.operation == Operation.NO_OP:
        return state
    elif curr_command.operation == Operation.PWR_SUPPLY_CMD or \
        curr_command.operation == Operation.SERIAL_CMD or \
        curr_command.operation == Operation.RECOVERY or \
        curr_command.operation == Operation.RESTART or \
        curr_command.operation == Operation.BRING_OFFLINE or\
        curr_command.operation == Operation.POWER_OFF or\
        curr_command.operation == Operation.ENABLE or\
        curr_command.operation == Operation.BOOTED_FORCE:
        logging.info(str(curr_command))
        return await generic_command(state, curr_command)
    else:
        RuntimeError(f'Operation {curr_command.operation} not recognized.')

async def generic_command(state, curr_command):
    # Get component to manipulate
    comp = state['hil'].get_component(curr_command.target)
    try:
        # This is for serial commands
        await comp.command(operation=curr_command.operation, options=curr_command.options)
    except CommandWarning:
        log.warning(f'FAILED COMMAND {curr_command}')
    # No change to state, so pass back
    return state

class Command(object):
    def __init__(self,
                 json_data='',
                 operation=Operation.NO_OP,
                 options=None,
                 target=''
                 ):
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
        d = {'operation': self.operation.value, 'options': self.options, 'target': self.target}
        return f'{json.dumps(d)}\n'

