#!/usr/bin/python
# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
from hil_config import VCU_CONFIGS
from hilcode.components import VCU, HIL
from hilcode.command import Command, Operation, CommandWarning
from contextvars import ContextVar
import logging
import asyncio
import argparse
import sys
import json
import pprint
from aiohttp import web

DEBUG = False

CYCLE_TIME = 1

if DEBUG:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

log_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')
log = logging.getLogger(__name__)
log.setLevel(LOG_LEVEL)
log.addHandler(log_handler)

# Globals
command_queue = ContextVar('command_queue')
telemetry_queue = ContextVar('telemetry_queue')
routes = web.RouteTableDef()

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
        'telemetry_queue': asyncio.Queue(200)
    }


async def execute_command(state, curr_command):
    """
    Function for deciding how to execute command.

    :param state: State of program
    :param curr_command: Command to execute
    """
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
        logging.info(f'COMMAND RECEIVED: {str(curr_command)}')
        stack, comp = state['hil'].get_component_cmdstack(curr_command.target)
        try:
            # Inform stack command is being sent
            if stack is not None:
                for upper_comp in stack:
                    await upper_comp.command_callstack(curr_command)
            # Send command to component
            await comp.command(operation=curr_command.operation, options=curr_command.options)
        except CommandWarning:
            log.warning(f'FAILED COMMAND {curr_command}')
    else:
        RuntimeError(f'Operation {curr_command.operation} not recognized.')

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

    log.debug('Telem to http')
    # Telem Out
    if tlm_queue.full():
        await tlm_queue.get()
    tlm_queue.put_nowait(ts_data)
    log.debug('Telem to file')

    # Write telem to log file
    ts_data_json = json.dumps(ts_data)
    with open(log_filename, 'a') as lf:
        lf.write(f'{ts_data_json}\n')

    # Return state for next processing round
    log.debug('End cycle')
    return state


async def json_server(reader, writer):
    """
    JSON command socket server.

    :param reader: Socket stream reader
    :param writer: Socket stream writer
    """
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

@routes.get('/')
async def handler(request):
    """
    HTTP Request Handler, for telemetry

    :param request: Request to HTTP
    :return: JSON response.
    """
    tlm_queue = telemetry_queue.get()
    tl = []
    while not tlm_queue.empty():
        tl.append(await tlm_queue.get())
    return web.json_response(tl)

# Main Function
async def main(args):
    """
    Runs setup() function once, then every second runs 'run' function.

    :param args: Arguments from argparse
    :return: N/A
    """
    # General State Setup
    state = await setup(args)
    command_queue.set(state['command_queue'])
    telemetry_queue.set(state['telemetry_queue'])

    # Command Server Setup
    cmd_factory = await asyncio.start_server(json_server, *('localhost', args['parser_port']))

    # Telemetry HTTP Server Setup
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', args['telem_port'])
    await site.start()

    log.debug(f'Starting up json server on port {args["parser_port"]}')

    # Main loop
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
        asyncio.run(main(vars(args)), debug=DEBUG)
    except KeyboardInterrupt:
        print('Exiting...')
