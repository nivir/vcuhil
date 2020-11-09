from supply_commander import SorensenXPF6020DP
import abc
import pprint


class Component(object):
    def __init__(self, name):
        self.name = name
        self.components = {}
        self.type = 'Component'

    async def setup(self, name):
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