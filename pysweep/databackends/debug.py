import pysweep.databackends.base as base

class DebugDataBackend(base.DataBackend, base.DataSaver):
    def __init__(self):
        pass

    def setup(self, paramstructure):
        print(paramstructure)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_to_line(self, line):
        print(line)

    def write_line(self):
        pass

    def write_block(self):
        pass

