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
                tc = TelemetryPoint(value['name'], timestamp, value['value'])
            elif value['type'] == 'string':
                tc = StringTelemetryPoint(value['name'], timestamp, value['value'])
            elif value['type'] == 'boolean':
                tc = BooleanTelemetryPoint(value['name'], timestamp, value['value'])
            elif value['type'] == 'float':
                tc = FloatTelemetryPoint(value['name'], timestamp, value['value'])
            elif value['type'] == 'unit':
                tc = UnitTelemetryPoint(value['name'], timestamp, value['value'], value['unit'])
            else:
                raise RuntimeError('Telemetry type not recognized')
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
        self.points = []
        self.type = 'default'

    def add_point(self, point):
        self.points.append(point)

    def get_points(self):
        return [point.get_dict() for point in self.points]

    def pop_points(self):
        points = [point.get_dict() for point in self.points]
        self.points = []
        return points

    def pop_point(self):
        return self.points.pop()


class TelemetryPoint(object):
    def __init__(self, name, timestamp, value):
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.type = 'default'

    def get_dict(self):
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value,
            'type': self.type
        }

    def __str__(self):
        return json.dumps(self.get_dict())

class StringTelemetryPoint(TelemetryPoint):
    def __init__(self, name, timestamp, value):
        super().__init__(name, timestamp, value)
        self.type = 'string'

class BooleanTelemetryPoint(TelemetryPoint):
    def __init__(self, name, timestamp, value):
        super().__init__(name, timestamp, value)
        self.type = 'boolean'

class FloatTelemetryPoint(TelemetryPoint):
    def __init__(self, name, timestamp, value):
        super().__init__(name, timestamp, value)
        self.type = 'float'

class UnitTelemetryPoint(FloatTelemetryPoint):
    def __init__(self, name, timestamp, value, unit):
        super().__init__(name, timestamp, value)
        self.unit = unit
        self.value = value
        self.type = 'unit'

    def get_dict(self):
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value,
            'type': self.type,
            'unit': self.unit
        }

# class UnitTelemetryPoint(TelemetryPoint):
#     def __init__(self, name, timestamp, value, unit):
#         super().__init__(name, timestamp, value)
#         ureg = UnitRegistry()
#         self.unit = getattr(ureg, unit)
#         self.value = value * self.unit
#         self.type = 'unit'
#
#     def get_dict(self):
#         return {
#             'name': self.name,
#             'timestamp': self.timestamp,
#             'value': self.value.magnitude,
#             'type': self.type,
#             'unit': str(self.unit)
#         }


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
        data = {f'{prefix}{self.name}.{name}':x.pop_points() for name, x in self.telemetry_channels.items()}
        # TODO(bhendrix) FIX HACK, why are we doing it this way again?
        for name, points in data.items():
            for point in points:
                point['name'] = name
        # All telem keepers
        for tk_name, tk in self.telemetry_keepers.items():
            tk_data = tk.current_data_dict(prefix=f'{prefix}{self.name}.')
            data.update(tk_data)
        return data

    def timestamped_data(self):
        data = self.current_data_dict()
        ts_list = []
        for name, points in data.items():
            for point in points:
                ts_list.append((point['timestamp'], point))
        return ts_list




