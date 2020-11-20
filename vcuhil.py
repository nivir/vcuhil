#!/usr/bin/env python3

import abc
import argparse
import socket
import pprint
import hil_config
import hilcode.command as command
import hilcode.telemetry as telemetry
import logging
import requests

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
log = logging.Logger('VCUHIL_client')
log.setLevel(logging.DEBUG)

BUFFER_SIZE = 64*1024

def check_command(cmd):
    """
    If this is a command object, do nothing.  However, if it's a string, try to convert JSON in string to
    a command object.

    :param cmd: String containting JSON command, or command object.
    :return: Command Object, either passed in or representing what's in the string.
    """
    # Check to see if it's a command, convert from JSON string if not
    if not isinstance(cmd, command.Command):
        if isinstance(cmd, str):
            cmd = command.Command(json_data=cmd)
        else:
            raise command.CommandError(f'Command object is not a JSON string or command object {cmd}')
    return cmd


class VCUHIL_command(object):
    """
    Client for HIL commands.
    """

    def __init__(self, host, cmd_port=8080):
        """
        Generate a HIL command client.

        :param host: Command client hostname
        :param cmd_port: Command client port (default of 8080)
        """
        self.host = host
        self.port = cmd_port

    def command(self, cmd):
        """
        Send a command to the HIL service.

        :param cmd: HIL command to send to service for execution
        :return: Response from HIL
        """
        cmd_socket = socket.create_connection((self.host, self.port))
        cmd = check_command(cmd)
        bcmd = str(cmd).encode()
        cmd_socket.send(bcmd)
        r = cmd_socket.recvmsg(BUFFER_SIZE)
        cmd_socket.close()
        return r


class VCUHIL_telemetry(object):
    """
    HIL Telemetry Client
    """

    def __init__(self, host, telem_port=8888):
        """
        Generate a HIL telemetry client.

        :param host: Telemetry client hostname
        :param telem_port: Telemetry client port (default of 8888)
        """
        self.host = host
        self.port = telem_port

    def get_telem(self):
        """
        Get a telemetry point from server

        :return: List of telemetry points from server
        """
        tlm_r = requests.get(f'http://{self.host}:{self.port}/')
        tlm_j = tlm_r.json()
        return telemetry.TelemetryJsonLine(tlm_j)


class ComponentClient(object):
    """
    Abstraction layer, allows control of generic HIL components.
    """

    def __init__(self, name, host, cmd_port=8080, config=None):
        """
        Generic HIL component

        :param name:  Name of HIL component
        :param host:  Hostname of HIL component (usually hil service)
        :param cmd_port:  Port to use to command HIL component (usually hil service port)
        :param config: Configuration dictionary for component.
        """
        self.host = host
        self.cmd_port = cmd_port
        self.name = name
        self.config = config
        for name, subcomponent_cfg in self.config.items():
            self.configure_subcomponent(name, subcomponent_cfg)

        @abc.abstractmethod
        def configure_subcomponent(self, name, subcomponent_config):
            """
            ABSTRACT METHOD.  Accepts a subcomponent configuration dictionary, and configures component.

            :param self: This component.
            :param name:  Name of component.
            :param subcomponent_config:  Configuration dicitionary for subcomponent.
            :return:
            """
            pass

        @abc.abstractmethod
        def command(self, cmd):
            """
            ABSTRACT METHOD.  Sends a command to HIL service to command component.

            :param self: This component.
            :param cmd: Command to send component.
            :return:
            """
            pass


class MicroClient(ComponentClient):
    """
    Client to send commands to Microcontrollers (HIA/HIB/LPA) on HIL.
    """

    def __init__(self, name, host, cmd_port=8080, config=None):
        """
        Microcontroller HIL component

        :param name:  Name of HIL component
        :param host:  Hostname of HIL component (usually hil service)
        :param cmd_port:  Port to use to command HIL component (usually hil service port)
        :param config: Configuration dictionary for component.
        """
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        """
        Setup for client (there's very little here)

        :param name: Name of subcomponent
        :param subcomponent_config:
        :return:
        """
        self.subcomponent_name = name

    def command(self, cmd):
        """
        Send a command (always a serial command) to the HIL.

        :param cmd: Command to send to microcontroller.
        :return:
        """
        cmd_client = VCUHIL_command(self.host, cmd_port=self.cmd_port)
        return cmd_client.command(command.Command(
            operation=command.Operation.SERIAL_CMD,
            target=self.name,
            options={'command':cmd.options['command']}
        ))



class PowerSupplyClient(ComponentClient):
    """
    Client to send commands to VCU Power Supply on HIL.
    """

    def __init__(self, name, host, cmd_port=8080, config=None):
        """
        Power Supply HIL component

        :param name:  Name of HIL component
        :param host:  Hostname of HIL component (usually hil service)
        :param cmd_port:  Port to use to command HIL component (usually hil service port)
        :param config: Configuration dictionary for component.
        """
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        """
        Setup for client (there's very little here)

        :param name: Name of subcomponent
        :param subcomponent_config:
        :return:
        """
        self.subcomponent_name = name

    def command(self, cmd):
        """
        Send a command to the HIL.

        :param cmd: Command to send to microcontroller.
        :return:
        """
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
        """
        Set channel 1 voltage.

        :param voltage: Voltage setpoint
        :return:
        """
        return self._generic_command('set_voltage_channel1', float(voltage))

    def set_voltage_channel2(self, voltage):
        """
        Set channel 2 voltage.

        :param voltage: Voltage Setpoint
        :return:
        """
        return self._generic_command('set_voltage_channel2', float(voltage))

    def set_current_channel1(self, current):
        """
        Set channel 1 maximum current.

        :param current: Current setpoint
        :return:
        """
        return self._generic_command('set_current_channel1', float(current))

    def set_current_channel2(self, current):
        """
        Set channel 2 maximum current.

        :param current: Current setpoint
        :return:
        """
        return self._generic_command('set_current_channel2', float(current))

    def set_output_channel1(self, boolean):
        """
        Set channel 1 output state

        :param boolean: True for enable, False for disable
        :return:
        """
        return self._generic_command('set_output_channel1', bool(boolean))

    def set_output_channel2(self, boolean):
        """
        Set channel 2 output state

        :param boolean: True for enable, False for disable
        :return:
        """
        return self._generic_command('set_output_channel2', bool(boolean))

class VCUClient(ComponentClient):
    """
    Client to send commands to VCU on HIL.
    """

    def __init__(self, name, host, cmd_port=8080, config=None):
        """
        Power Supply HIL component

        :param name:  Name of HIL component
        :param host:  Hostname of HIL component (usually hil service)
        :param cmd_port:  Port to use to command HIL component (usually hil service port)
        :param config: Configuration dictionary for component.
        """
        self.subcomponents = {}
        super().__init__(name, host, cmd_port=cmd_port, config=config)

    def configure_subcomponent(self, name, subcomponent_config):
        """
        Configure a subcomponent of the HIL

        :param name: Name of subcomponent
        :param subcomponent_config: Dictionary of configuration options for subcomponent
        :return:
        """
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
        """
        Send a command to the VCU on the HIL

        :param cmd: Command object to send.
        :return:
        """
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
    """
    Combined telemetry and command client for VCU on HIL.
    """

    def __init__(self, host, cmd_port=8080, telem_port=8888):
        """
        Generate a combined client for VCU.

        :param host: Hostname of VCU HIL
        :param cmd_port: Command port of VCU HIL (default is 8080)
        :param telem_port: Telemetry port of VCU HIL (default is 8888)
        """
        self.host = host
        self.telem_port = telem_port
        vcu_config = hil_config.VCU_CONFIGS
        self.vcus = {name:VCUClient(name, host, cmd_port, config) for name,config in vcu_config.items()}

    def get_telem_dict(self):
        """
        Get current telemetry points from server.

        :return: Current telemetry points.
        """

        tlm = VCUHIL_telemetry(self.host, self.telem_port)
        lines = tlm.get_telem()
        return lines.get_point_list()


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