from hilcode.supply_commander import SorensenXPF6020DP
import abc
import pprint
from transitions import Machine
from pint import UnitRegistry
from hilcode.telemetry import TelemetryKeeper, UnitTelemetryChannel, StringTelemetryChannel, BooleanTelemetryChannel


class Component(object):
    def __init__(self, name):
        self.name = name
        self.components = {}
        self.type = 'Component'
        self.telemetry = TelemetryKeeper('Component')

    async def setup(self, name):
        await self.gather_telemetry_keepers(name)

    @abc.abstractmethod
    def all_configs(self):
        pass

    async def gather_telemetry(self):
        for _, comp in self.components.items():
            await comp.gather_telemetry()

    async def gather_telemetry_keepers(self, name):
        for _, comp in self.components.items():
            self.telemetry.add_telemetry_keeper(comp.telemetry)


class HIL(Component):
    states = ['idle', 'flash_vcu']

    def __init__(self, name):
        super().__init__(name)
        self.type = 'HIL'
        self.hil_machine = Machine(model=self, states=HIL.states, initial='idle')
        self.telemetry = TelemetryKeeper('HIL')

    def all_configs(self):
        def _config_gen():
            for comp_name, comp_value in self.components.items():
                yield comp_name, comp_value.all_configs()

        return {n:v for n,v in _config_gen()}

    async def setup(self, name):
        for component_name, component in self.components.items(): # Grab VCU
            await component.setup(component_name)
        await super().setup(name)

    def __str__(self):
        nl = '\n'
        config = ''.join([f'{x.type} {x_name}{nl}-=CONFIG=-{nl}{str(x)}{nl}{nl}'
                          for x_name,x in  self.components.items()])
        return f"HIL: {self.name}{nl}{config}"

    def get_component(self, name):
        return self.components[name]


class VCU(Component):
    states = ['power_off', 'booting', 'idle', 'command', 'recovery']

    def __init__(self, name, configs):
        super().__init__(name)
        self.configs = configs
        self.type = 'VCU'
        self.vcu_machine = Machine(model=self, states=VCU.states, initial='power_off')
        self._setup_transitions()
        self.telemetry = TelemetryKeeper(name)
        self._setup_telemetry()

    def _setup_telemetry(self):
        # HIL State
        self.telemetry.add_telemetry_channel(StringTelemetryChannel('vcu_state'))


    def _setup_transitions(self):
        # Can power off VCU at any time
        self.vcu_machine.add_transition(trigger='power_off', source='*', dest='power_off')

        # Power Off -> Booting machine state
        self.vcu_machine.add_transition(trigger='power_on', source='power_off', dest='booting')

        # Wait for unit to boot
        self.vcu_machine.add_transition(trigger='booted', source='booting', dest='idle')

        # Once booted, we can go to command or recovery mode
        self.vcu_machine.add_transition(trigger='cmd', source='idle', dest='command')
        self.vcu_machine.add_transition(trigger='recover', source='idle', dest='recovery')

        # Can reboot any time (assume this takes out of recovery mode
        self.vcu_machine.add_transition(trigger='reboot', source='*', dest='booting')

        # Command Complete, go back to idle
        self.vcu_machine.add_transition(trigger='cmd_complete', source='command', dest='idle')

    async def gather_telemetry(self):
        self.telemetry.telemetry_channels['vcu_state']\
            .set_value_with_immediate_timestamp(self.state)
        await super().gather_telemetry()

    def all_configs(self):
        return self.configs

    async def setup(self, name):
        for config_dev, config_dict in self.configs.items():
            if   'sorensen_psu' in config_dict['type']:
                self.components[config_dev] = PowerSupply(f'{self.name}.psu_{self.name}', SorensenXPF6020DP())
                await self.components[config_dev].client.connect(config_dict['host'], config_dict['port'])
                await self.components[config_dev].setup(f'{self.name}.psu_{self.name}')
            elif 'micro' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'sga' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'hpa' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
            elif 'vlan' in config_dict['type']:
                self.components[config_dev] = Component(config_dev) #TODO(bhendrix) replace with actual object
        await super().setup(name)

    async def query_power_status(self):
        return await self.components['psu'].query_state()

    def __str__(self):
        return pprint.pformat(self.configs)


class PowerSupply(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'PowerSupply'
        self.client = client
        self.telemetry = TelemetryKeeper(name)

    async def query_state(self):
        return await self.client.supply_state()

    def power_status(self):
        return self.client.supply_state()

    def all_configs(self):
        return {}

    async def setup(self, name):
        self._setup_telemetry(name)
        await super().setup(name)


    async def gather_telemetry(self):
        # Get Power Status
        power_status = await self.power_status()
        self.telemetry.telemetry_channels['pri_meas_volt']\
            .set_value_with_immediate_timestamp(power_status[1]['meas_voltage'])
        self.telemetry.telemetry_channels['red_meas_volt']\
            .set_value_with_immediate_timestamp(power_status[2]['meas_voltage'])
        self.telemetry.telemetry_channels['pri_set_volt']\
            .set_value_with_immediate_timestamp(power_status[1]['set_voltage'])
        self.telemetry.telemetry_channels['red_set_volt']\
            .set_value_with_immediate_timestamp(power_status[2]['set_voltage'])
        self.telemetry.telemetry_channels['pri_meas_curr']\
            .set_value_with_immediate_timestamp(power_status[1]['meas_current'])
        self.telemetry.telemetry_channels['red_meas_curr']\
            .set_value_with_immediate_timestamp(power_status[2]['meas_current'])
        self.telemetry.telemetry_channels['pri_set_curr']\
            .set_value_with_immediate_timestamp(power_status[1]['set_current'])
        self.telemetry.telemetry_channels['red_set_curr']\
            .set_value_with_immediate_timestamp(power_status[2]['set_current'])
        self.telemetry.telemetry_channels['pri_output_enable']\
            .set_value_with_immediate_timestamp(power_status[1]['output_enabled'])
        self.telemetry.telemetry_channels['red_output_enable']\
            .set_value_with_immediate_timestamp(power_status[2]['output_enabled'])
        await super().gather_telemetry()

    def _setup_telemetry(self, name):
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('pri_meas_volt', UnitRegistry().volts))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('red_meas_volt', UnitRegistry().volts))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('pri_set_volt', UnitRegistry().volts))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('red_set_volt', UnitRegistry().volts))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('pri_meas_curr', UnitRegistry().amperes))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('red_meas_curr', UnitRegistry().amperes))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('pri_set_curr', UnitRegistry().amperes))
        self.telemetry.add_telemetry_channel(UnitTelemetryChannel('red_set_curr', UnitRegistry().amperes))
        self.telemetry.add_telemetry_channel(BooleanTelemetryChannel('pri_output_enable'))
        self.telemetry.add_telemetry_channel(BooleanTelemetryChannel('red_output_enable'))