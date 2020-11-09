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

    logging.info(hil)
    logging.info(pprint.pformat(await hil.query_power_status()))
    logging.info('-=NINJA TURTLES GO=-')

    return hil


# Loop
async def run(setup_out):
    hil = setup_out
    comps = hil.components
    for comp_name,comp in comps.items():
        if 'VCU' in comp.type:
            vcu_power_status = await comp.query_power_status()
            status = \
                f"VCU: {comp_name}\tCurr1: {vcu_power_status[1]['meas_current']}\tCurr2: {vcu_power_status[2]['meas_current']}"
            logging.info(status)
    logging.debug('Tick Tock')


async def periodic_run(cycle_time, state):
    await asyncio.sleep(cycle_time)
    await run(state)

# Main Function
async def main(args):
    state = await setup(args)
    while True:
        task = asyncio.create_task(periodic_run(CYCLE_TIME, state))
        if task.done():
            state = task.result()
            continue
        else:
            await asyncio.sleep(CYCLE_TIME)


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
    asyncio.run(main(vars(args)), debug=True)
