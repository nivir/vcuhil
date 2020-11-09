# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
from hil_config import VCU_CONFIGS
from hilcode.components import VCU, HIL
import logging
import asyncio
import argparse
import pprint
import time
import sys
import transitions

CYCLE_TIME = 1

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('VCUHIL_service')
log.setLevel(logging.DEBUG)

# Setup
async def setup(args):
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
        'hil': hil
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
    comps = hil.components

    # Send Commands

    # Acquire Data for next cycle
    await hil.gather_telemetry()
    telem_str = str(hil.telemetry)
    print(telem_str)
    logging.info(telem_str)

    # Determine actions next cycle

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

# Main Function
async def main(args):
    """
    Runs setup() function once, then every second runs 'run' function.

    :param args: Arguments from argparse
    :return: N/A
    """
    state = await setup(args)
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
    try:
        asyncio.run(main(vars(args)), debug=True)
    except KeyboardInterrupt:
        print('Exiting...')