import time
import pprint
import json

class TelemetryJsonLine(object):
    def __init__(self, json_in):
        self.telemetry = []
        dump = json.loads(json_in)
        for timestamp, value in dump.items():
            tc = TelemetryChannel(value['name'])
            tc.set_value(timestamp, value['value'])
            self.telemetry.append(tc)

    def __str__(self):
        json_data = []
        for tlm_ch in self.telemetry:
            json_data.append({'name': tlm_ch.name, 'timestamp': tlm_ch.timestamp, 'value': tlm_ch.value})
        return json.dumps(json_data)

    def get_channels_dict(self):
        data = []
        for tlm_ch in self.telemetry:
            data.append({'name': tlm_ch.name, 'timestamp': tlm_ch.timestamp, 'value': tlm_ch.value})
        return data


class TelemetryChannel(object):
    def __init__(self, name):
        self.name = name
        self.value = None
        self.timestamp = time.time()

    def set_value(self, timestamp, value):
        self.timestamp = timestamp
        self.value = value

    def set_value_with_immediate_timestamp(self, value):
        self.set_value(time.time(), value)

    def __str__(self):
        return json.dumps({'name': self.name, 'timestamp': self.timestamp, 'value': self.value})

class StringTelemetryChannel(TelemetryChannel):
    pass

class BooleanTelemetryChannel(TelemetryChannel):
    pass

class UnitTelemetryChannel(TelemetryChannel):
    def __init__(self, name, unit):
        super().__init__(name)
        self.unit = unit

    def set_value(self, timestamp, value):
        super().set_value(timestamp, value * self.unit)


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
        return pprint.pformat(self.current_data())

    def current_data(self, prefix=''):
        data = {f'{prefix}{self.name}.{name}':{
            'timestamp': x.timestamp,
            'value': x.value
        } for name, x in self.telemetry_channels.items()}
        for tk_name, tk in self.telemetry_keepers.items():
            tk_data = tk.current_data(prefix=f'{prefix}{self.name}.')
            data.update(tk_data)
        return data

    def timestamped_data(self):
        data = self.current_data()
        return {
                t_v['timestamp']: {
                    'name': name,
                    'value': t_v['value']
                }
            for name, t_v in data.items() }




