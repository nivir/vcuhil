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


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('')


class Component(object):
    def __init__(self, name):
        self.name = name
        self.components = {}
        self.type = 'Component'

    @abc.abstractmethod
    def setup(self, name):
        pass

    @abc.abstractmethod
    def all_configs(self):
        pass



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
        for component_name, component in self.components.items():
            await component.setup(component_name)


    def __str__(self):
        nl = '\n'
        config = ''.join([f'{x.type} {x_name}{nl}-=CONFIG=-{nl}{str(x)}{nl}{nl}'
                          for x_name,x in  self.components.items()])
        return f"HIL: {self.name}{nl}{config}"

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

    def __str__(self):
        return pprint.pformat(self.configs)

class PowerSupply(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'PowerSupply'
        self.client = client

    async def setup(self, name):
        print(f'name is {name}')
        print('configuring')

    def query_state(self):
        return self.client.supply_state()


# Setup
async def setup():
    # Parse Config
    hil = HIL('VCU HIL')
    for vcu_name, vcu_config in VCU_CONFIGS.items():
        vcu = VCU(vcu_name, vcu_config)
        hil.components[vcu_name] = vcu

    # Setup Components
    await hil.setup('VCU HIL')

    logging.debug(hil)

    return hil


# Loop
async def run(hil):
    leonardo = hil.components['leonardo']
    michalangelo = hil.components['michalangelo']
    donatello = hil.components['donatello']
    raphael = hil.components['raphael']

    print('-= LEONARDO =-')
    print(await leonardo.components['psu'].query_state())
    print('-= MICHALANGELO =-')
    print(await michalangelo.components['psu'].query_state())
    print('-= DONATELLO =-')
    print(await donatello.components['psu'].query_state())
    print('-= RAPHAEL =-')
    print(await raphael.components['psu'].query_state())
    print('-= NINJA TURTLES GO =-')

# Main Function
async def main(args):
    args = await setup()
    return await run(args)


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
