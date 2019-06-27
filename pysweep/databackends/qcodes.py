import pysweep.databackends.base as base


class DataBackend(base.DataBackend, base.DataSaver):
    def __init__(self, meas):
        self.meas = meas  # The qcodes measurement object
        self.runner = None
        self.datasaver = None
        self.columns = None

    def setup(self, paramstructure):
        setpoints = []
        self.columns = []
        for param in paramstructure:
            self.columns.append(param.name)
            if param.independent:
                self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype)
                setpoints.append(param.name)
            else:
                self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype,
                                                    setpoints=setpoints)

    def __enter__(self):
        self.runner = self.meas.run()
        self.datasaver = self.runner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.runner.__exit__(exc_type, exc_val, exc_tb)

    def add_to_line(self, line):
        self.datasaver.add_result(*line)

    def write_line(self):
        pass

