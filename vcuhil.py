#!/bin/python3

import abc
import socket
import hil_config
import hilcode.command as command
import hilcode.telemetry as telemetry

def check_command(cmd):
    # Check to see if it's a command, convert from JSON string if not
    if not isinstance(cmd, command.Command):
        if isinstance(cmd, str):
            cmd = command.Command(json_data=cmd)
        else:
            raise command.CommandError(f'Command object is not a JSON string or command object {cmd}')
    return cmd


class VCUHIL_command(object):
    def __init__(self, host, cmd_port=8080):
        self.host = host
        self.port = cmd_port

    def command(self, cmd):
        cmd_socket = socket.create_connection((self.host, self.port))
        cmd = check_command(cmd)
        bcmd = str(cmd).encode()
        cmd_socket.send(bcmd)
        r = cmd_socket.recvmsg(16384)
        cmd_socket.close()
        return r


class VCUHIL_telemetry(object):
    def __init__(self, host, telem_port=8888):
        self.host = host
        self.port = telem_port

    def get_telem(self):
        cmd_socket = socket.create_connection((self.host, self.port))
        r = cmd_socket.recvmsg(16384)
        cmd_socket.close()
        return telemetry.TelemetryJsonLine(r[0])


class ComponentClient(object):
    def __init__(self, name, host, cmd_port=8080, config=None):
        self.host = host
        self.cmd_port = cmd_port
        self.name = name
        self.config = config
        for name, subcomponent_cfg in self.config.items():
            self.configure_subcomponent(name, subcomponent_cfg)

        @abc.abstractmethod
        def configure_subcomponent(self, name, subcomponent_config):
            pass

class PowerSupplyClient(ComponentClient):
    def __init__(self, name, host, cmd_port=8080, config=None):
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        self.subcomponent_name = name

    def _generic_command(self, cmd, val):
        cmd_client = VCUHIL_command(self.host, cmd_port=self.cmd_port)
        return cmd_client.command(command.Command(
            operation=command.Operation.PWR_SUPPLY_CMD,
            target=self.name,
            options={'command':cmd, 'value': val}
        ))

    def set_voltage_channel1(self, voltage):
        return self._generic_command('set_voltage_channel1', float(voltage))

    def set_voltage_channel2(self, voltage):
        return self._generic_command('set_voltage_channel2', float(voltage))

    def set_current_channel1(self, current):
        return self._generic_command('set_current_channel1', float(current))

    def set_current_channel2(self, current):
        return self._generic_command('set_current_channel2', float(current))

    def set_output_channel1(self, boolean):
        return self._generic_command('set_output_channel1', bool(boolean))

    def set_output_channel2(self, boolean):
        return self._generic_command('set_output_channel2', bool(boolean))

class VCUClient(ComponentClient):
    def __init__(self, name, host, cmd_port=8080, config=None):
        self.subcomponents = {}
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        if 'sorensen_psu' in subcomponent_config['type']:
            self.subcomponents[name] = PowerSupplyClient(f'{self.name}.{name}', self.host, cmd_port=self.cmd_port, config=subcomponent_config)

class VCUHILClient(object):
    def __init__(self, host, cmd_port=8080, telem_port=8888):
        self.host = host
        self.telem_port = telem_port
        vcu_config = hil_config.VCU_CONFIGS
        self.vcus = {name:VCUClient(name, host, cmd_port, config) for name,config in vcu_config.items()}

    def get_telem_dict(self):
        tlm = VCUHIL_telemetry(self.host, self.telem_port)
        lines = tlm.get_telem()
        return lines.get_channels_dict()

