import pprint
import json

class TelemetryJsonLine(object):
    """
    Convenience object, converts a JSON line that's known to be telemetry to a list of telemetry points
    """
    def __init__(self, dump):
        """
        Process a JSON string containing telemetry data.

        :param dump: JSON string
        """
        self.telemetry = []
        if dump != '':
            for line in dump:
                for timestamp, value in line:
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
        """
        Produce a JSON representation of telemetry data.

        :return: JSON representation of state
        """
        return json.dumps(self.get_point_list())

    def get_point_list(self):
        """
        Get a list of every telemetry point

        :return: List of telemetry points
        """
        return [tlm_ch.get_dict() for tlm_ch in self.telemetry]


class TelemetryChannel(object):
    """
    A telemetry channel, which contains a list of points that have accumulated about that channel.
    """

    def __init__(self, name):
        """
        Create a telemetry channel

        :param name: Name of channel
        """
        self.name = name
        self.points = []
        self.type = 'default'

    def add_point(self, point):
        """
        Add a telemetry point

        :param point: Telemetry point
        """
        self.points.append(point)

    def get_points(self):
        """
        Get all telemetry points

        :return: All telemetry points in channel currently
        """
        return [point.get_dict() for point in self.points]

    def pop_points(self):
        """
        Pop all telemetry points in channel currently.  This removes the points from the channel.

        :return: All telemetry points in channel currently
        """
        points = [point.get_dict() for point in self.points]
        self.points = []
        return points

    def pop_point(self):
        """
        Pop latest telemetry point from channel, removing it

        :return: Latest telemetry point from channel
        """
        return self.points.pop()


class TelemetryPoint(object):
    """
    Generic Telemetry Point (You probably want a child class)
    """

    def __init__(self, name, timestamp, value):
        """
        Create a telemetry point

        :param name: Name of channel
        :param timestamp: Timestamp of telemetry point
        :param value: Value of telemetry point
        """
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.type = 'default'

    def get_dict(self):
        """
        Get dictionary representation of telemetry point

        :return: Dictionary representation of telemetry point
        """
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value,
            'type': self.type
        }

    def __str__(self):
        """
        String representation of point (in JSON)

        :return: JSON representation of point
        """
        return json.dumps(self.get_dict())

class StringTelemetryPoint(TelemetryPoint):
    """
    A telemetry point containing a string value.
    """
    def __init__(self, name, timestamp, value):
        """
        Create a telemetry point containing a string value

        :param name: Name of channel
        :param timestamp: Timestamp of telemetry point
        :param value: Value of telemetry point (string)
        """
        super().__init__(name, timestamp, value)
        self.type = 'string'

class BooleanTelemetryPoint(TelemetryPoint):
    """
    A telemetry point containing a boolean value.
    """
    def __init__(self, name, timestamp, value):
        """
        Create a telemetry point containing a boolean value

        :param name: Name of channel
        :param timestamp: Timestamp of telemetry point
        :param value: Value of telemetry point (boolean)
        """
        super().__init__(name, timestamp, value)
        self.type = 'boolean'

class FloatTelemetryPoint(TelemetryPoint):
    """
    A telemetry point containing a float value.
    """
    def __init__(self, name, timestamp, value):
        """
        Create a telemetry point containing a float value

        :param name: Name of channel
        :param timestamp: Timestamp of telemetry point
        :param value: Value of telemetry point (float)
        """
        super().__init__(name, timestamp, value)
        self.type = 'float'

class UnitTelemetryPoint(FloatTelemetryPoint):
    """
    A telemetry point containing a float value and unit string.
    """
    def __init__(self, name, timestamp, value, unit):
        """
        Create a telemetry point containing a float value and a unit string

        :param name: Name of channel
        :param timestamp: Timestamp of telemetry point
        :param value: Value of telemetry point (float)
        :param unit: Unit associated with point
        """
        super().__init__(name, timestamp, value)
        self.unit = unit
        self.value = value
        self.type = 'unit'

    def get_dict(self):
        """
        Get dictionary representation of telemetry point

        :return: Dictionary representation of telemetry point
        """
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'value': self.value,
            'type': self.type,
            'unit': self.unit
        }


class TelemetryKeeper(object):
    """
    Class for managing multiple telemetry channels associated with an object.
    """

    def __init__(self, name):
        """
        Collection of telemetry channels

        :param name: Name for set of telemetry channels
        """
        self.name = name
        self.telemetry_channels = {}
        self.telemetry_keepers = {}

    def purge(self, name):
        """
        Remove telemetry channels from list.

        :param name: Name of channel to remove
        """
        if name in self.telemetry_channels.keys():
            self.telemetry_channels.pop(name)
        elif name in self.telemetry_keepers.keys():
            self.telemetry_keepers.pop(name)
        else:
            RuntimeError(f'{name} not found in telemetry channels or keepers.')

    def add_telemetry_channel(self, channel):
        """
        Add a telemetry channel to the collection.

        :param channel: Telemetry channel to add
        """
        self.telemetry_channels[channel.name] = channel

    def add_telemetry_keeper(self, keeper):
        """
        Add another keeper (a set of telemetry channels) to this keeper.

        :param keeper: Keeper with telemetry channels to add to this keeper as a subset
        """
        self.telemetry_keepers[keeper.name] = keeper

    def __str__(self):
        """
        Pretty formatted text of all telemetry objects

        :return: Pretty formatted list of telemetry objects
        """
        return pprint.pformat(self.current_data_dict())

    def current_data_dict(self, prefix=''):
        """
        Dump status of all telemetry objects in keeper.

        :param prefix: Append this prefix to each telemetry object name.
        :return: Dictionary containing all telemetry objects.
        """
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
        """
        Dump status of all telemetry objects in keeper, but in a list of tuples contianing (timestamp, data_point)

        :return: List of tuples containing (timestamp, data_point)
        """
        data = self.current_data_dict()
        ts_dict = {}
        for name, points in data.items():
            for point in points:
                #remove extraneous timestamp
                timestamp = point['timestamp']
                if point['type'] == 'unit':
                    point = {
                        'name': point['name'],
                        'type': point['type'],
                        'value': point['value'],
                        'unit': point['unit']
                    }
                else:
                    point = {
                        'name': point['name'],
                        'type': point['type'],
                        'value': point['value']
                    }
                # Create timestamped dict
                if timestamp in ts_dict.keys():
                    ts_dict[timestamp].append(point)
                else:
                    ts_dict[timestamp] = [point]
        return ts_dict




