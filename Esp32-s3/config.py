class Config:
    PINS = {
        'display': {
            'sck': 14,
            'mosi': 13,
            'cs': 15,
            'dc': 0,
            'rst': 2
        },
        'sensors': {
            'dht11': 5,
            'mq135': 0,
            'led': 16
        }
    }

    WIFI = {
        'ssid': 'TP-Link_E921',
        'password': '92929265',
        'timeout': 20
    }

    DISPLAY = {
        'width': 128,
        'height': 160,
        'spi_freq': 20000000
    }

    MEASUREMENTS = {
        'interval': 2,
        'count': 10,
        'retries': 3
    }
