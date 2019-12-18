import pysweep.databackends.base as base

class ListDataBackend(base.DataBackend, base.DataSaver):
    def __init__(self):
        self.paramstruct = None
        self.lines = []

    def setup(self, paramstructure, dict_waterfall):
        self.paramstruct = paramstructure

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_to_line(self, line):
        self.lines.append(line)

    def write_line(self):
        pass

    def write_block(self):
        pass

