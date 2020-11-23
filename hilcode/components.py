from hilcode.supply_commander import SorensenXPF6020DP
from hilcode.micro_commander import VCUSerialDevice
from hilcode.sga_commander import VCUSGA
from hilcode.hpa_commander import VCUHPA
import abc
import pprint
import asyncio
import time
from transitions import Machine
from hilcode.telemetry import TelemetryKeeper, TelemetryChannel, BooleanTelemetryPoint, StringTelemetryPoint, UnitTelemetryPoint, FloatTelemetryPoint
from hilcode.command import CommandWarning, Operation
import logging

log = logging.getLogger(__name__)

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

    @abc.abstractmethod
    async def command(self, operation, options):
        pass

    async def command_callstack(self, cmd):
        pass

    async def close(self):
        pass

    async def check_state(self):
        for _, comp in self.components.items():
            await comp.check_state()

    async def gather_telemetry(self):
        for _, comp in self.components.items():
            await comp.gather_telemetry()

    async def gather_telemetry_keepers(self, name):
        for _, comp in self.components.items():
            self.telemetry.add_telemetry_keeper(comp.telemetry)

    def get_component(self, name):
        if '.' in name:
            tokens = str(name).split('.')
            context = self
            for token in tokens:
                context =  context.get_component(token)
            return context
        else:
            return self.components[name]

    def get_component_cmdstack(self, name):
        if '.' in name:
            tokens = str(name).split('.')
            context = self
            prev_context = []
            for token in tokens:
                prev_context.append(context)
                context =  context.get_component(token)
            return prev_context, context
        else:
            return None, self.components[name]


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

    async def command(self, operation, options):
        pass


    def __str__(self):
        nl = '\n'
        config = ''.join([f'{x.type} {x_name}{nl}-=CONFIG=-{nl}{str(x)}{nl}{nl}'
                          for x_name,x in  self.components.items()])
        return f"HIL: {self.name}{nl}{config}"



class VCU(Component):
    states = ['power_off', 'booting', 'idle', 'command', 'recovery', 'offline']
    transitions = [
        {'trigger': 'power_off', 'source':'*', 'dest':'power_off'},
        {'trigger': 'power_on', 'source': 'power_off', 'dest': 'booting'},
        {'trigger': 'booted', 'source': 'booting', 'dest': 'idle'},
        {'trigger': 'cmd', 'source': 'idle', 'dest': 'command'},
        {'trigger': 'recover', 'source': 'idle', 'dest': 'recovery'},
        {'trigger': 'reboot', 'source': '*', 'dest': 'booting'},
        {'trigger': 'cmd_complete', 'source': 'command', 'dest': 'idle'},
        {'trigger': 'bring_offline', 'source': '*', 'dest': 'offline'}
    ]

    def _setup_state_callbacks(self):
        pass
        #self.vcu_machine.on_enter_offline('desetup')
        #self.vcu_machine.on_enter_power_off('resetup')

    async def exec_booting(self):
        if await self.ping_hpa_sga():
            log.debug(f'VCU {self.name} booted.')
            self.booted()

    async def exec_idle(self):
        if not await self.ping_hpa_sga():
            log.debug(f'VCU {self.name} disconnected')
            self.reboot()


    async def check_state(self):
        if self.state == 'booting':
            return await self.exec_booting()
        elif self.state == 'idle':
            return await self.exec_idle()
        else:
            pass

    async def command_callstack(self, cmd):
        if cmd.operation == Operation.SERIAL_CMD:
            if self.state == 'idle':
                if cmd.target == f'{self.name}.hia':
                    if cmd.options['command'] == 'tegrareset x1':
                        self.reboot()

    async def command(self, operation, options):
        if operation == Operation.BRING_OFFLINE:
            logging.info(f'Bringing VCU {self.name} offline.')
            await self.desetup()
            self.bring_offline()
        elif operation == Operation.POWER_OFF:
            logging.info(f'Bringing VCU {self.name} to power_off state.')
            await self.desetup()
            await self.setup(self.name)
            self.power_off()
        elif operation == Operation.ENABLE:
            if self.state == 'power_off':
                logging.info(f'Bringing VCU {self.name} power up.')
                await self.components['psu'].enable()
                self.power_on()
            else:
                RuntimeWarning('ENABLE command can only be called in power_off sate.')
        elif operation == Operation.BOOTED_FORCE:
            if self.state == 'booting':
                logging.info(f'Forcing VCU {self.name} into idle state.')
                self.booted()
            else:
                RuntimeWarning('Force Boot command can only be called in booting sate.')
        else:
            logging.error('WTF A VCU COMMAND?')
            raise RuntimeError('A VCU COMMAND?  NOT IN THIS HOUSE')

    async def desetup(self):
        logging.debug(f'VCU {self.name} is being desetup')
        for comp_name, comp in self.components.items():
            await comp.close()
            self.telemetry.purge(comp_name)
        self.components = {}

    def __init__(self, name, configs):
        super().__init__(name)
        self.configs = configs
        self.type = 'VCU'
        self.vcu_machine = Machine(model=self, states=VCU.states, transitions=VCU.transitions, initial='power_off')
        self.telemetry = TelemetryKeeper(name)
        self._setup_telemetry()
        self._setup_state_callbacks()

    def _setup_telemetry(self):
        # HIL State
        self.telemetry.add_telemetry_channel(TelemetryChannel('vcu_state'))

    async def gather_telemetry(self):
        self.telemetry.telemetry_channels['vcu_state'].add_point(
            StringTelemetryPoint(
                'vcu_state',
                time.time(),
                self.state
            )
        )
        await super().gather_telemetry()

    def all_configs(self):
        return self.configs

    async def setup(self, name):
        logging.debug(f'Setting up VCU {self.name} alias {name}')
        for config_dev, config_dict in self.configs.items():
            if   'sorensen_psu' in config_dict['type']:
                # Create a power supply component
                self.components[config_dev] = PowerSupply('psu', SorensenXPF6020DP(), defaults=config_dict['defaults'])
                # Connect telnet client for power supply to actual physical power supply
                await self.components[config_dev].client.connect(config_dict['host'], config_dict['port'])
                # Complete setup for power supply
                await self.components[config_dev].setup('psu')
            elif 'micro' in config_dict['type']:
                self.components[config_dev] = Micro(f'micro_{config_dev}', VCUSerialDevice())
                await self.components[config_dev].client.connect(config_dict['serial'], baudrate=config_dict['baudrate'])
                await self.components[config_dev].setup(f'micro_{config_dev}')
            elif 'sga' in config_dict['type']:
                self.components[config_dev] = SGA(
                    config_dev,
                    VCUSGA(config_dict['odb'])
                )
                await self.components[config_dev].setup('sga')
            elif 'hpa' in config_dict['type']:
                self.components[config_dev] = HPA(
                    config_dev,
                    VCUHPA(
                        config_dict['sga_odb'],
                        config_dict['hostname']
                    )
                )
                await self.components[config_dev].setup('hpa')
            elif 'vlan' in config_dict['type']:
                self.components[config_dev] = Component(config_dev)
            else:
                raise RuntimeError(f'Unexpected VCU subcomponent type {config_dict["type"]}.')
        await super().setup(name)

    async def query_power_status(self):
        return await self.components['psu'].query_state()

    def __str__(self):
        return pprint.pformat(self.configs)

    async def ping_hpa_sga(self):
        sga = await self._ping_sga()
        if not sga:
            return sga
        return await self._ping_hpa_through_sga()

    async def _ping_sga(self):
        return self.components['sga'].is_connected()

    async def _ping_hpa_through_sga(self):
        return self.components['hpa'].is_connected()


class Micro(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'Micro'
        self.client = client

    def all_configs(self):
        return {}

    async def setup(self, name):
        await super().setup(name)
        await self.client.start()
        self._setup_telemetry(name)

    async def command(self, operation, options):
        return await self.client.command(options)

    async def close(self):
        return await self.client.close()

    async def gather_telemetry(self):
        try:
            while self.client.line_available():
                line = self.client.get_line_nowait()
                log.debug(f'Serial Input from {self.name}: {line}')
                self.telemetry.telemetry_channels['serial_out'].add_point(
                    StringTelemetryPoint(
                        'serial_out',
                        line.time,
                        line.data
                    )
                )
        except asyncio.QueueEmpty:
            pass
        await super().gather_telemetry()

    def _setup_telemetry(self, name):
        self.telemetry.add_telemetry_channel(TelemetryChannel('serial_out'))

class HPA(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'HPA'
        self.client = client
        self.telemetry = TelemetryKeeper(name)

    async def setup(self, name):
        await super().setup(name)
        await self.client.setup()
        self.telemetry.add_telemetry_channel(TelemetryChannel('ssh_connected'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('uname_version'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('nvidia_version'))

    async def close(self):
        return await self.client.close()

    async def gather_telemetry(self):
        self.telemetry.telemetry_channels['ssh_connected'].add_point(
            BooleanTelemetryPoint(
                'connected',
                time.time(),
                self.client.is_connected()
            )
        )
        self.telemetry.telemetry_channels['uname_version'].add_point(
            StringTelemetryPoint(
                'uname_version',
                time.time(),
                self.client.uname_version()
            )
        )
        self.telemetry.telemetry_channels['nvidia_version'].add_point(
            StringTelemetryPoint(
                'nvidia_version',
                time.time(),
                self.client.nvidia_version()
            )
        )

    def is_connected(self):
        return self.client.is_connected()

class SGA(Component):
    def __init__(self, name, client):
        super().__init__(name)
        self.type = 'SGA'
        self.client = client
        self.telemetry = TelemetryKeeper(name)

    async def setup(self, name):
        await super().setup(name)
        await self.client.setup()
        self.telemetry.add_telemetry_channel(TelemetryChannel('ssh_connected'))

    async def close(self):
        return await self.client.close()

    async def gather_telemetry(self):
        self.telemetry.telemetry_channels['ssh_connected'].add_point(
            BooleanTelemetryPoint(
                'connected',
                time.time(),
                self.client.is_connected()
            )
        )

    def is_connected(self):
        return self.client.is_connected()

class PowerSupply(Component):
    def __init__(self, name, client, defaults):
        super().__init__(name)
        self.type = 'PowerSupply'
        self.client = client
        self.defaults = defaults
        self.telemetry = TelemetryKeeper(name)

    async def query_state(self):
        return await self.client.supply_state()

    def power_status(self):
        return self.client.supply_state()

    def all_configs(self):
        return {}

    async def setup(self, name):
        await super().setup(name)
        self._setup_telemetry(name)

    async def enable(self):
        await self.client.set_output_channel1(1)
        await self.client.set_output_channel2(1)
        return

    async def command(self, operation, options):
        try:
            if options['command'] == 'set_defaults':
                await self.client.set_voltage_channel1(self.defaults['voltage_ch1'])
                await self.client.set_voltage_channel2(self.defaults['voltage_ch2'])
                await self.client.set_current_channel1(self.defaults['current_ch1'])
                await self.client.set_current_channel2(self.defaults['current_ch2'])
                await self.client.set_output_channel1(self.defaults['output_ch1'])
                await self.client.set_output_channel2(self.defaults['output_ch2'])
                return
            else:
                func = getattr(self.client, options['command'])
                return await func(options['value'])
        except KeyError:
            raise CommandWarning(f'Command {options} failed.')
        except AttributeError:
            raise CommandWarning(f'Command {options} failed.')

    async def close(self):
        return await self.client.close()

    async def gather_telemetry(self):
        # Get Power Status
        power_status = await self.power_status()
        self.telemetry.telemetry_channels['idn'].add_point(
            StringTelemetryPoint(
                'idn',
                time.time(),
                power_status[0]['idn']
            )
        )
        self.telemetry.telemetry_channels['pri_meas_volt'].add_point(
            UnitTelemetryPoint(
                'pri_meas_volt',
                time.time(),
                power_status[1]['meas_voltage'],
                'volts'
            )
        )
        self.telemetry.telemetry_channels['red_meas_volt'].add_point(
            UnitTelemetryPoint(
                'red_meas_volt',
                time.time(),
                power_status[2]['meas_voltage'],
                'volts'
            )
        )
        self.telemetry.telemetry_channels['pri_set_volt'].add_point(
            UnitTelemetryPoint(
                'red_meas_volt',
                time.time(),
                power_status[1]['set_voltage'],
                'volts'
            )
        )
        self.telemetry.telemetry_channels['red_set_volt'].add_point(
            UnitTelemetryPoint(
                'red_meas_volt',
                time.time(),
                power_status[2]['set_voltage'],
                'volts'
            )
        )
        self.telemetry.telemetry_channels['pri_meas_curr'].add_point(
            UnitTelemetryPoint(
                'pri_meas_curr',
                time.time(),
                power_status[1]['meas_current'],
                'amperes'
            )
        )
        self.telemetry.telemetry_channels['red_meas_curr'].add_point(
            UnitTelemetryPoint(
                'red_meas_curr',
                time.time(),
                power_status[2]['meas_current'],
                'amperes'
            )
        )
        self.telemetry.telemetry_channels['pri_set_curr'].add_point(
            UnitTelemetryPoint(
                'red_meas_curr',
                time.time(),
                power_status[1]['set_current'],
                'amperes'
            )
        )
        self.telemetry.telemetry_channels['red_set_curr'].add_point(
            UnitTelemetryPoint(
                'red_meas_curr',
                time.time(),
                power_status[2]['set_current'],
                'amperes'
            )
        )
        self.telemetry.telemetry_channels['pri_output_enable'].add_point(
            BooleanTelemetryPoint(
                'pri_output_enable',
                time.time(),
                power_status[1]['output_enabled']
            )
        )
        self.telemetry.telemetry_channels['red_output_enable'].add_point(
            BooleanTelemetryPoint(
                'red_output_enable',
                time.time(),
                power_status[2]['output_enabled']
            )
        )
        await super().gather_telemetry()

    def _setup_telemetry(self, name):
        self.telemetry.add_telemetry_channel(TelemetryChannel('idn'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('pri_meas_volt'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('red_meas_volt'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('pri_set_volt'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('red_set_volt'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('pri_meas_curr'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('red_meas_curr'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('pri_set_curr'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('red_set_curr'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('pri_output_enable'))
        self.telemetry.add_telemetry_channel(TelemetryChannel('red_output_enable'))