# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
from hil_config import VCU_CONFIGS
from hilcode.components import VCU, HIL
from hilcode.command import Command, Operation, execute_command
import logging
import asyncio
import argparse
import time
import sys
import pint
import json
import pprint

CYCLE_TIME = 1

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('VCUHIL_service')
log.setLevel(logging.DEBUG)

# Globals
command_queue = asyncio.Queue()

# Setup
async def setup(args):
    """
    One-time run setup function (before second-by-second execution

    :param args: Arguments from command line
    :return: State of HIL
    """
    # Parse Config
    hil = HIL('VCU HIL')
    for vcu_name, vcu_config in VCU_CONFIGS.items():
        vcu = VCU(vcu_name, vcu_config)
        hil.components[vcu_name] = vcu

    # Setup Components
    await hil.setup('VCU HIL')
    logging.info('-=NINJA TURTLES GO=-')

    return {
        'done': False,
        'hil': hil,
        'log_filename': args['log_filename'],
    }

# Loop (every second)
async def run(state):
    """
    Function that runs once per second.  If it takes longer, blocks next call for run().

    :param state: State of program, can be manipulated by function.
    :return: Manipulated state
    """
    # Setup
    hil = state['hil']
    log_filename = state['log_filename']
    cmd_queue = command_queue

    # Send Commands
    if not cmd_queue.empty():
        curr_command = cmd_queue.get_nowait()
    else:
        curr_command = Command(operation=Operation.NO_OP)

    state = await execute_command(state, curr_command)

    # Acquire Data for next cycle
    await hil.gather_telemetry()
    ts_data = hil.telemetry.timestamped_data()
    logging.debug(pprint.pformat(ts_data))
    ts_data_raw = {}
    for ts, n_v in ts_data.items():
        if isinstance(n_v['value'], pint.Quantity):
            ts_data_raw[ts] = {
                'name': n_v['name'],
                'value': n_v['value'].magnitude
            }
        else:
            ts_data_raw[ts] = {
                'name': n_v['name'],
                'value': n_v['value']
            }
    with open(log_filename, 'a') as lf:
        lf.write(f'{json.dumps(ts_data_raw)}\n')

    # Return state for next processing round
    return state


async def periodic_run(cycle_time, state):
    """
    DO NOT USE, you probably want 'run' instead.

    This function is a helper that helps to set up a periodically executing function.

    :param cycle_time:  How often to run function
    :param state: State to pass between runs
    :return: Ouptut state of run function
    """
    start_time = time.time()
    new_state = await run(state)
    # Calculate time to wait
    wait_time = cycle_time - (time.time() - start_time)
    await asyncio.sleep(wait_time) # IDLE Time
    return new_state


async def json_server(reader, writer):
    while True:
        data = await reader.readline()
        try:
            message = data.decode()
            command_options = json.loads(message)
            cmd = Command(Operation(command_options['operation']), command_options['options'], command_options['target'])
            await command_queue.put(cmd)
            data = ['ACK']
            writer.write(json.dumps(data).encode())
        except json.JSONDecodeError:
            data = ['INVALID JSON']
            writer.write(json.dumps(data).encode())
        except KeyError:
            data = ['INVALID CMD']
            writer.write(json.dumps(data).encode())


# Main Function
async def main(args):
    """
    Runs setup() function once, then every second runs 'run' function.

    :param args: Arguments from argparse
    :return: N/A
    """
    state = await setup(args)
    factory = await asyncio.start_server(json_server, *('localhost', args['parser_port']))
    log.debug(f'Starting up json server on port {args["parser_port"]}')

    while not state['done']:
        task = asyncio.create_task(periodic_run(CYCLE_TIME, state))
        if task.done():
            state = task.result()
            continue
        else:
            await asyncio.sleep(CYCLE_TIME)
    # No longer running, 'done' called
    logging.info('Service Terminated')
    sys.exit(0) # Terminated properly


# Command Line Interface
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='vcuhil_service',
                                     description='Service to manage VCU HIL on main x86 computer (April).')
    parser.add_argument(
        '--log_filename',
        default='log.json'
    )
    parser.add_argument(
        '--parser_port',
        default=8080
    )
    args = parser.parse_args()
    try:
        asyncio.run(main(vars(args)), debug=True)
    except KeyboardInterrupt:
        print('Exiting...')