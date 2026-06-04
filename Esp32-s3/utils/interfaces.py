class SensorInterface:
    def read_data(self):
        raise NotImplementedError


class DataStorageInterface:
    def save_measurement(self, measurement_data):
        raise NotImplementedError


class DisplayInterface:
    def show_measurement(self, measurement_num, total_measurements, sensor_data):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError