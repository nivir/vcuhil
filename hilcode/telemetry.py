import time
import pprint

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
        return f'{self.name}:\t@{str(self.timestamp)} VALUE {str(self.value)}'

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

    def add_telemetry_channel(self, channel):
        self.telemetry_channels[channel.name] = channel

    def add_telemetry_keeper(self, keeper):
        self.telemetry_keepers[f'{self.name}.{keeper.name}'] = keeper

    def __str__(self):
        return pprint.pformat(self.current_data())

    def current_data(self):
        data = {f'{self.name}.{name}':{
            'timestamp': x.timestamp,
            'value': x.value
        } for name, x in self.telemetry_channels.items()}
        for tk_name, tk in self.telemetry_keepers.items():
            tk_data = tk.current_data()
            #tk_data = {f'{self.name}.{name}':x for name,x in tk_data.items()}
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




