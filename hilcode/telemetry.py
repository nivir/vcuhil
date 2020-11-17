import time
from pint import UnitRegistry
import pprint
import json

class TelemetryJsonLine(object):
    def __init__(self, json_in):
        self.telemetry = []
        dump = json.loads(json_in)
        for timestamp, value in dump:
            if value['type'] == 'default':
                tc = TelemetryChannel(value['name'])
            elif value['type'] == 'string':
                tc = StringTelemetryChannel(value['name'])
            elif value['type'] == 'boolean':
                tc = BooleanTelemetryChannel(value['name'])
            elif value['type'] == 'unit':
                unit = getattr(UnitRegistry(), value['unit'])
                tc = UnitTelemetryChannel(value['name'], unit)
            else:
                raise RuntimeError('Telemetry type not recognized')
            tc.set_value(timestamp, value['value'])
            self.telemetry.append(tc)

    def __str__(self):
        return json.dumps(self.get_channels_list())

    def get_channels_list(self):
        return [tlm_ch.get_dict() for tlm_ch in self.get_telemetry()]

    def get_telemetry(self):
        return [tlm_ch for tlm_ch in self.telemetry]



class TelemetryChannel(object):
    def __init__(self, name):
        self.name = name
        self.value = None
        self.timestamp = time.time()
        self.type = 'default'

    def set_value(self, timestamp, value):
        self.timestamp = timestamp
        self.value = value

    def set_value_with_immediate_timestamp(self, value):
        self.set_value(time.time(), value)

    def get_dict(self):
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value,
            'type': self.type
        }

    def __str__(self):
        return json.dumps(self.get_dict())

class StringTelemetryChannel(TelemetryChannel):
    def __init__(self, name):
        super().__init__(name)
        self.type = 'string'

class BooleanTelemetryChannel(TelemetryChannel):
    def __init__(self, name):
        super().__init__(name)
        self.type = 'boolean'

class UnitTelemetryChannel(TelemetryChannel):
    def __init__(self, name, unit):
        super().__init__(name)
        self.type = 'unit'
        self.unit = unit

    def set_value(self, timestamp, value):
        super().set_value(timestamp, value * self.unit)

    def get_dict(self):
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value.magnitude,
            'type': self.type,
            'unit': str(self.unit)
        }


class TelemetryKeeper(object):
    def __init__(self, name):
        self.name = name
        self.telemetry_channels = {}
        self.telemetry_keepers = {}

    def purge(self, name):
        if name in self.telemetry_channels.keys():
            self.telemetry_channels.pop(name)
        elif name in self.telemetry_keepers.keys():
            self.telemetry_keepers.pop(name)
        else:
            RuntimeError(f'{name} not found in telemetry channels or keepers.')

    def add_telemetry_channel(self, channel):
        self.telemetry_channels[channel.name] = channel

    def add_telemetry_keeper(self, keeper):
        self.telemetry_keepers[keeper.name] = keeper

    def __str__(self):
        return pprint.pformat(self.current_data_dict())

    def current_data_dict(self, prefix=''):
        # All Telem Channels
        data = {f'{prefix}{self.name}.{name}':x.get_dict() for name, x in self.telemetry_channels.items()}
        # All telem keepers
        for tk_name, tk in self.telemetry_keepers.items():
            tk_data = tk.current_data_dict(prefix=f'{prefix}{self.name}.')
            data.update(tk_data)
        return data

    def timestamped_data(self):
        data = self.current_data_dict()
        return [ (t_v['timestamp'], t_v) for name, t_v in data.items() ]




