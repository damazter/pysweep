import pysweep

class Slave:
    def __init__(self, station):
        pysweep.STATION = station

    def run_measurement(self, command):
        pass