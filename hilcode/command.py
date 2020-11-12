from enum import Enum
import logging


async def execute_command(state, curr_command):
    logging.info(str(curr_command))
    if curr_command.operation == Operation.NO_OP:
        logging.debug(f'NO_OP COMMAND RECIEVED')
        return state
    elif curr_command.operation == Operation.PWR_SUPPLY_CMD:
        return power_supply_command(state, curr_command)
    elif curr_command.operation == Operation.SERIAL_CMD:
        return serial_command(state, curr_command)
    elif curr_command.operation == Operation.RECOVERY:
        return recovery(state, curr_command)
    elif curr_command.operation == Operation.RESTART:
        return restart(state, curr_command)
    elif curr_command.operation == Operation.WAIT_ON_VAR:
        return wait_on_var(state, curr_command)
    elif curr_command.operation == Operation.SSH_CMD:
        return ssh_cmd(state, curr_command)
    else:
        RuntimeError(f'Operation {curr_command.operation} not recognized.')

async def power_supply_command(state, curr_command):
    # Get component to manipulate
    comp = state['HIL'].get_component(curr_command.target)
    await comp.command(curr_command['options'])
    # No change to state, so pass back
    return state

async def serial_command(state, curr_command):
    # Get component to manipulate
    comp = state['HIL'].get_component(curr_command.target)
    await comp.command(curr_command['options'])
    return state

async def recovery(state, curr_command):
    return state

async def restart(state, curr_command):
    return state

async def wait_on_var(state, curr_command):
    return state

async def ssh_cmd(state, curr_command):
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
