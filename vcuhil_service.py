# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
from hil_config import VCU_CONFIGS
from hilcode.components import VCU, HIL
from hilcode.command import Command, Operation, execute_command
from contextvars import ContextVar
import logging
import asyncio
import argparse
import sys
import json
import pprint

CYCLE_TIME = 1

LOG_LEVEL = logging.INFO

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(LOG_LEVEL)

# Globals
command_queue = ContextVar('command_queue')
telemetry_queue = ContextVar('telemetry_queue')

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
    log.info('-=NINJA TURTLES GO=-')

    return {
        'done': False,
        'hil': hil,
        'log_filename': args['log_filename'],
        'command_queue': asyncio.Queue(),
        'telemetry_queue': asyncio.LifoQueue()
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

    cmd_queue = state['command_queue']
    tlm_queue = state['telemetry_queue']

    # Send Commands
    if not cmd_queue.empty():
        curr_command = cmd_queue.get_nowait()
    else:
        curr_command = Command(operation=Operation.NO_OP)

    log.debug(f'Executing command {curr_command}')
    state = await execute_command(state, curr_command)

    await hil.check_state()

    # Acquire Data for next cycle
    log.debug('Command complete, now getting telemetry')
    await hil.gather_telemetry()
    ts_data = hil.telemetry.timestamped_data()
    log.debug('Telemetry Got')
    log.debug(pprint.pformat(ts_data))

    ts_data_json = json.dumps(ts_data)
    log.debug('Telem to socket')
    # Telem Out
    if tlm_queue.full():
        await telemetry_queue.get()
    tlm_queue.put_nowait(f'{ts_data_json}\n')
    log.debug('Telem to file')

    # Write telem to log file
    with open(log_filename, 'a') as lf:
        lf.write(f'{ts_data_json}\n')

    # Return state for next processing round
    log.debug('End cycle')
    return state


async def json_server(reader, writer):
    data = await reader.readline()
    cmd_queue = command_queue.get()
    try:
        message = data.decode()
        command_options = json.loads(message)
        cmd = Command(
            operation=Operation(command_options['operation']),
            options=command_options['options'],
            target=command_options['target']
        )
        await cmd_queue.put(cmd)
        data = ['ACK']
        writer.write(json.dumps(data).encode())
    except json.decoder.JSONDecodeError:
        data = ['INVALID JSON']
        writer.write(json.dumps(data).encode())
    except KeyError:
        data = ['INVALID CMD']
        writer.write(json.dumps(data).encode())
    except ValueError:
        data = ['INVALID CMD']
        writer.write(json.dumps(data).encode())
    finally:
        writer.close()

async def telem_server(reader, writer):
    tlm_queue = telemetry_queue.get()
    tl = await tlm_queue.get()
    writer.write(str(tl).encode())
    writer.close()

# Main Function
async def main(args):
    """
    Runs setup() function once, then every second runs 'run' function.

    :param args: Arguments from argparse
    :return: N/A
    """
    state = await setup(args)
    command_queue.set(state['command_queue'])
    telemetry_queue.set(state['telemetry_queue'])


    cmd_factory = await asyncio.start_server(json_server, *('localhost', args['parser_port']))
    telem_factory = await asyncio.start_server(telem_server, *('localhost', args['telem_port']))
    log.debug(f'Starting up json server on port {args["parser_port"]}')

    while not state['done']:
        log.debug('Launching new task')
        task = asyncio.create_task(run(state))
        log.debug('Waiting for Task to end')
        await asyncio.sleep(CYCLE_TIME)
        log.debug('Task should have ended by now....')
        while not task.done():
            log.debug('Task did not end, wait for it to end')
            await asyncio.sleep(CYCLE_TIME)
        log.debug('Task Complete, saving results')
        state = task.result()
    # No longer running, 'done' called
    log.info('Service Terminated')
    cmd_factory.close()
    telem_factory.close()
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
    parser.add_argument(
        '--telem_port',
        default=8888
    )
    args = parser.parse_args()
    try:
        asyncio.run(main(vars(args)), debug=False)
    except KeyboardInterrupt:
        print('Exiting...')