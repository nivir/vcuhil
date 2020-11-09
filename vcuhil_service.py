# VCU HIL Service
# Baird Hendrix
# (c) 2020 Luminar Technologies

# Imports
from hil_config import VCU_CONFIGS
import logging
import sys, os
from supply_commander import SorensenXPF6020DP
import asyncio
import argparse
import abc
import pprint

CYCLE_TIME = 1

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('VCUHIL_service')
log.setLevel(logging.DEBUG)


class Component(object):
    def __init__(self, name):
        self.name = name
        self.components = {}
        self.type = 'Component'

    def setup(self):
        pass

    @abc.abstractmethod
    def all_configs(self):
        pass

    async def query_power_status(self):
        return {name:await comp.query_power_status() for name, comp in self.components.items()}



class HIL(Component):
    def __init__(self, name):
        super().__init__(name)
        self.type = 'HIL'

    def all_configs(self):
        def _config_gen():
            for comp_name, comp_value in self.components.items():
                yield comp_name, comp_value.all_configs()

        return {n:v for n,v in _config_gen()}

    async def setup(self, name):
        for component_name, component in self.components.items(): # Grab VCU
            await component.setup(component_name)

    def __str__(self):
        nl = '\n'
        config = ''.join([f'{x.type} {x_name}{nl}-=CONFIG=-{nl}{str(x)}{nl}{nl}'
                          for x_name,x in  self.components.items()])
        return f"HIL: {self.name}{nl}{config}"

    def get_component(self, name):
        return self.components[name]

class VCU(Component):
    def __init__(self, name, configs):
        super().__init__(name)
        self.configs = configs
        self.type = 'VCU'

    def all_configs(self):
        return self.configs

    async def setup(self, name):
        for config_dev, config_dict in self.configs.items():
            if   'sorensen_psu' in config_dict['type']:
                self.components[config_dev] = PowerSupply(f'psu_{self.name}', SorensenXPF6020DP())
                await self.components[config_dev].client.connect(config_dict['host'], config_dict['port'])
            elif 'micro' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'sga' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'hpa' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'vlan' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object

    async def query_power_status(self):
        return await self.components['psu'].query_state()

    def __str__(self):
        return pprint.pformat(self.configs)


class PowerSupply(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'PowerSupply'
        self.client = client

    async def query_state(self):
        return await self.client.supply_state()

    def power_status(self):
        return self.client.supply_state()

    def all_configs(self):
        return {}


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
