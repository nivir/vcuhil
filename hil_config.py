HIL_IP = '172.31.255.78'


PSU_DEFAULTS = {
    'voltage_ch1': 16.0,
    'voltage_ch2': 16.0,
    'current_ch1': 7.0,
    'current_ch2': 7.0,
    'output_ch1': 0,
    'output_ch2': 0
}

VCU_DEFAULT_AUTO_IPS = {
    'sga': '172.16.66.1',
    'hpa': '172.16.66.2'
}


PDU_CONFIGS = {
    'pdu1': {
        'type': 'pdu',
        'hostname': 'pdu1',
        'plugs': {
            1: {'name': 'psu-leonardo'},
            2: {'name': 'vector-leonardo'},
            3: {'name': 'psu-michalangelo'},
            4: {'name': 'vector-michalangelo'},
            5: {'name': 'psu-donatello'},
            6: {'name': 'vector-donatello'},
            7: {'name': 'psu-raphael'},
            8: {'name': 'vector-raphael'},
        }
    },
    'pdu2': {
        'type': 'pdu',
        'hostname': 'pdu2',
        'plugs': {
            1: {'name': 'serial-usb-hub'},
            2: {'name': 'recovery-usb-hub'},
            3: {'name': 'x86-april'},
            4: {'name': 'lidar'},
        }
    },
}


LIDAR_CONFIGS = {
    'vlan': {
        'type': 'vlan',
        'vlan': 42,
    },
    'window_lidar': {
        'type': 'lidar_h',
        'hostname': '10.42.0.210',  # TODO(baird) Change to real address.
    }
}

VCU_CONFIGS = {
    # 'leonardo': {
    #     'vlan': {
    #         'type': 'vlan',
    #         'vlan': 11,
    #     },
    #     'sga': {
    #         'type': 'sga',
    #         'hostname': 'vcu-leonardo-sga',
    #         'odb': 'vcu-leonardo-odb',
    #         'serial': '/dev/tty_vcu_leonardo_sga',
    #         'baudrate': 115200,
    #     },
    #     'hpa': {
    #         'type': 'hpa',
    #         'hostname': 'vcu-leonardo-hpa',
    #         'serial': '/dev/tty_vcu_leonardo_hpa',
    #         'baudrate': 115200,
    #     },
    #     'hia': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_leonardo_hia',
    #         'baudrate': 115200,
    #     },
    #     'hib': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_leonardo_hib',
    #         'baudrate': 115200,
    #     },
    #     'lpa': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_leonardo_lpa',
    #         'baudrate': 115200,
    #     },
    #     'psu': {
    #         'type': 'sorensen_psu',
    #         'host': 'psu-leonardo',
    #         'port': 9221,
    #     }
    # },
    # 'michalangelo': {
    #     'vlan': {
    #         'type': 'vlan',
    #         'vlan': 12,
    #     },
    #     'sga': {
    #         'type': 'sga',
    #         'hostname': 'vcu-michalangelo-sga',
    #         'odb': 'vcu-michalangelo-odb',
    #         'serial': '/dev/tty_vcu_michalangelo_sga',
    #         'baudrate': 115200,
    #     },
    #     'hpa': {
    #         'type': 'hpa',
    #         'hostname': 'vcu-michalangelo-hpa',
    #         'serial': '/dev/tty_vcu_michalangelo_hpa',
    #         'baudrate': 115200,
    #     },
    #     'hia': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_michalangelo_hia',
    #         'baudrate': 115200,
    #     },
    #     'hib': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_michalangelo_hib',
    #         'baudrate': 115200,
    #     },
    #     'lpa': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_michalangelo_lpa',
    #         'baudrate': 115200,
    #     },
    #     'psu': {
    #         'type': 'sorensen_psu',
    #         'host': 'psu-michalangelo',
    #         'port': 9221,
    #     }
    # },
    'donatello': {
        'vlan': {
            'type': 'vlan',
            'vlan': 13,
        },
        'sga': {
            'type': 'sga',
            'hostname': 'vcu-donatello',
            'odb': 'vcu-donatello',
            'username': 'root',
            'password': 'root',
        },
        'hpa': {
            'type': 'hpa',
            'hostname': '172.16.66.2',
            'sga_odb': 'vcu-donatello',
            'username': 'root',
            'password': 'root',
        },
        'sga_serial': {
            'type': 'micro',
            'serial': '/dev/tty_vcu_donatello_sga',
            'baudrate': 115200,
        },
        'hpa_serial': {
            'type': 'micro',
            'serial': '/dev/tty_vcu_donatello_hpa',
            'baudrate': 115200,
        },
        'hia': {
            'type': 'micro',
            'serial': '/dev/tty_vcu_donatello_hia',
            'baudrate': 115200,
        },
        'hib': {
            'type': 'micro',
            'serial': '/dev/tty_vcu_donatello_hib',
            'baudrate': 115200,
        },
        'lpa': {
            'type': 'micro',
            'serial': '/dev/tty_vcu_donatello_lpa',
            'baudrate': 115200,
        },
        'psu': {
            'type': 'sorensen_psu',
            'host': 'psu-donatello',
            'port': 9221,
            'defaults': PSU_DEFAULTS,
        }
    },
    # 'raphael': {
    #     'vlan': {
    #         'type': 'vlan',
    #         'vlan': 14,
    #     },
    #     'sga': {
    #         'type': 'sga',
    #         'hostname': 'vcu-raphael-sga',
    #         'odb': 'vcu-raphael-odb',
    #         'serial': '/dev/tty_vcu_raphael_sga',
    #         'baudrate': 115200,
    #     },
    #     'hpa': {
    #         'type': 'hpa',
    #         'hostname': 'vcu-raphael-hpa',
    #         'serial': '/dev/tty_vcu_raphael_hpa',
    #         'baudrate': 115200,
    #     },
    #     'hia': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_raphael_hia',
    #         'baudrate': 115200,
    #     },
    #     'hib': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_raphael_hib',
    #         'baudrate': 115200,
    #     },
    #     'lpa': {
    #         'type': 'micro',
    #         'serial': '/dev/tty_vcu_raphael_lpa',
    #         'baudrate': 115200,
    #     },
    #     'psu': {
    #         'type': 'sorensen_psu',
    #         'host': 'psu-raphael',
    #         'port': 9221,
    #     }
    # },
}


