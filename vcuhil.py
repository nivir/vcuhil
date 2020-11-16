#!/usr/bin/env python3

import abc
import argparse
import socket
import pprint
import hil_config
import hilcode.command as command
import hilcode.telemetry as telemetry
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('VCUHIL_client')
log.setLevel(logging.DEBUG)

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

        @abc.abstractmethod
        def command(self, cmd):
            pass


class MicroClient(ComponentClient):
    def __init__(self, name, host, cmd_port=8080, config=None):
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        self.subcomponent_name = name

    def command(self, cmd):
        cmd_client = VCUHIL_command(self.host, cmd_port=self.cmd_port)
        return cmd_client.command(command.Command(
            operation=command.Operation.SERIAL_CMD,
            target=self.name,
            options={'command':cmd.options['command']}
        ))



class PowerSupplyClient(ComponentClient):
    def __init__(self, name, host, cmd_port=8080, config=None):
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        self.subcomponent_name = name

    def command(self, cmd):
        cmd_client = VCUHIL_command(self.host, cmd_port=self.cmd_port)
        return cmd_client.command(cmd)

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
        if subcomponent_config['type'] == 'sorensen_psu':
            self.subcomponents[name] = PowerSupplyClient(f'{self.name}.{name}', self.host,
                                                         cmd_port=self.cmd_port,
                                                         config=subcomponent_config
                                                         )
        elif subcomponent_config['type'] == 'micro':
            self.subcomponents[name] = MicroClient(f'{self.name}.{name}', self.host,
                                                   cmd_port=self.cmd_port,
                                                   config=subcomponent_config)

    def command(self, cmd):
        cmd_client = VCUHIL_command(self.host, cmd_port=self.cmd_port)
        if cmd.operation == command.Operation.BRING_OFFLINE:
            return cmd_client.command(command.Command(
                operation=command.Operation.BRING_OFFLINE,
                target=self.name,
                options=None
            ))
        elif cmd.operation == command.Operation.POWER_OFF:
            return cmd_client.command(command.Command(
                operation=command.Operation.POWER_OFF,
                target=self.name,
                options=None
            ))
        elif cmd.operation == command.Operation.ENABLE:
            return cmd_client.command(command.Command(
                operation=command.Operation.ENABLE,
                target=self.name,
                options=None
            ))
        elif cmd.operation == command.Operation.BOOTED_FORCE:
            return cmd_client.command(command.Command(
                operation=command.Operation.BOOTED_FORCE,
                target=self.name,
                options=None
            ))
        else:
            raise RuntimeError('Something else that is not a vcu offline')


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


def print_action_help():
    print('SYNTAX: vcuhil.py [action]')
    print('ACTION: telemetry\t\tGet and print one telemetry point.')
    print('ACTION: psu_set\t\tAdjust a power supply setting.')
    print('ACTION: serial_command\t\tSend an arbitrary command over a serial port.')
    print('ACTION: bring_offline\t\tSet a VCU to offline status.')
    print('ACTION: power_off\t\tCompletely power off VCU, and reinitialize all states.')
    print('ACTION: help\t\tPrint this message.')


def print_psu_set_help():
    print('SYNTAX: vcuhil.py psu_set [VCU] psu [setting] [value]')
    print('SETTING: voltage_ch1\t\tSet channel 1 voltage of power supply')
    print('SETTING: voltage_ch2\t\tSet channel 2 voltage of power supply')
    print('SETTING: current_ch1\t\tSet channel 1 current of power supply')
    print('SETTING: current_ch2\t\tSet channel 2 current of power supply')
    print('SETTING: output_ch1\t\tSet channel 1 output of power supply')
    print('SETTING: output_ch2\t\tSet channel 2 output of power supply')
    print('SETTING: set_defaults\t\tSet supply to default values for VCU.')


def main(args):
    hil = VCUHILClient(args.host, args.cmd_port, args.telem_port)
    if args.action == 'telemetry':
        pprint.pprint(hil.get_telem_dict())
    elif args.action == 'psu_set':
        if args.command == 'voltage_ch1':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_voltage_channel1(args.setpoint)
        elif args.command == 'voltage_ch2':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_voltage_channel2(args.setpoint)
        elif args.command == 'current_ch1':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_current_channel1(args.setpoint)
        elif args.command == 'current_ch2':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_current_channel2(args.setpoint)
        elif args.command == 'output_ch1':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_output_channel1(args.setpoint)
        elif args.command == 'output_ch2':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].set_output_channel2(args.setpoint)
        elif args.command == 'set_defaults':
            hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].command(command.Command(
                operation=command.Operation.PWR_SUPPLY_CMD,
                target=f'{args.vcu_name}.{args.subcomponent_name}',
                options={'command': 'set_defaults'}
            ))
        elif args.command == 'help':
            print_psu_set_help()
        else:
            raise RuntimeError(f'Command for psu_set {args.command} not recognized. Try "help" for a list of commands.')
    elif args.action == 'serial_cmd':
        hil.vcus[args.vcu_name].subcomponents[args.subcomponent_name].command(command.Command(
            operation=command.Operation.SERIAL_CMD,
            target=f'{args.vcu_name}.{args.subcomponent_name}',
            options={'command': args.command }
        ))
    elif args.action == 'bring_offline':
        hil.vcus[args.vcu_name].command(command.Command(
            operation=command.Operation.BRING_OFFLINE,
            target=args.vcu_name,
            options=None
        ))
    elif args.action == 'power_off':
        hil.vcus[args.vcu_name].command(command.Command(
            operation=command.Operation.POWER_OFF,
            target=args.vcu_name,
            options=None
        ))
    elif args.action == 'enable':
        hil.vcus[args.vcu_name].command(command.Command(
            operation=command.Operation.ENABLE,
            target=args.vcu_name,
            options=None
        ))
    elif args.action == 'force_booted':
        hil.vcus[args.vcu_name].command(command.Command(
            operation=command.Operation.BOOTED_FORCE,
            target=args.vcu_name,
            options=None
        ))
    elif args.action == 'help':
        print_action_help()
    else:
        raise RuntimeError('Not a handled action.')

if __name__=='__main__':
    parser = argparse.ArgumentParser(prog='vcuhil',
                                     description='Client to manage VCU HIL on main x86 computer (April).')
    parser.add_argument('action', default='telemetry', type=str, help='Action to execute')
    parser.add_argument('vcu_name', default=None, type=str, help='Target VCU', nargs='?')
    parser.add_argument('subcomponent_name', default=None, type=str, help='Target VCU component', nargs='?')
    parser.add_argument('command', default=None, type=str, help='(optional) Command of action', nargs='?')
    parser.add_argument('setpoint', default=None, type=float, help='(optional) Setpoint of action', nargs='?')
    parser.add_argument('--host', default='localhost', type=str, help='Host for HIL service')
    parser.add_argument('--cmd_port', default=8080, type=int, help='Host port for commanding HIL')
    parser.add_argument('--telem_port', default=8888, type=int, help='Host port for commanding HIL')

    args = parser.parse_args()
    main(args)