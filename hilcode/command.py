from enum import Enum
import logging

class CommandWarning(RuntimeWarning):
    pass


async def execute_command(state, curr_command):
    if curr_command.operation == Operation.NO_OP:
        return state
    elif curr_command.operation == Operation.PWR_SUPPLY_CMD or \
        curr_command.operation == Operation.SERIAL_CMD or \
        curr_command.operation == Operation.SSH_CMD or \
        curr_command.operation == Operation.RECOVERY or \
        curr_command.operation == Operation.RESTART:
        logging.info(str(curr_command))
        return await generic_command(state, curr_command)
    else:
        RuntimeError(f'Operation {curr_command.operation} not recognized.')

async def generic_command(state, curr_command):
    # Get component to manipulate
    comp = state['hil'].get_component(curr_command.target)
    try:
        await comp.command(curr_command.options)
    except CommandWarning:
        logging.warning(f'FAILED COMMAND {curr_command}')
    # No change to state, so pass back
    return state


class Operation(Enum):
    NO_OP = 0
    PWR_SUPPLY_CMD = 1
    SERIAL_CMD = 2
    RECOVERY = 3
    RESTART = 4
    WAIT_ON_VAR = 5
    FORCE_LOAD = 6


class Command(object):
    def __init__(self,
                 operation=Operation.NO_OP,
                 options={},
                 target=''
                 ):
        assert isinstance(operation, Operation)
        self.operation = operation
        self.options = options
        self.target = target


    def __str__(self):
        return f'COMMAND {self.operation}\tTARGET: {self.target}\tOPTIONS {self.options}'
