import time

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
        channel_data = '\n'.join([f'{self.name}.{str(x)}' for name,x in self.telemetry_channels.items()])
        # Append name to each channel in other keepers
        keeper_data = ''
        for tk_name, tk in self.telemetry_keepers.items():
            keeper_data += str(tk)
            keeper_data += '\n'
        return f'{channel_data}\n{keeper_data}'



