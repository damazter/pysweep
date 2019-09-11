import pysweep.databackends.base as base

STUPIDAXES = ['None1', 'None2', 'None3']

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
            # Hack to exclude trivial measurement axes
            if param.independent:
                if isinstance(param, base.DataParameterFixedSweep) and param.npoints==1:
                    print(param.name, ', postponing registration')
                else:
                    self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype)
                    setpoints.append(param.name)
            else:
                self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype,
                                                    setpoints=setpoints)
        # for param in paramstructure:
        #     # Hack to exclude trivial measurement axes
        #     if param.independent:
        #         if isinstance(param, base.DataParameterFixedSweep) and param.npoints==1:
        #             self.meas.register_custom_parameter(param.name, unit=param.unit, paramtype=param.paramtype, setpoints=setpoints)

    def __enter__(self):
        self.runner = self.meas.run()
        self.datasaver = self.runner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.runner.__exit__(exc_type, exc_val, exc_tb)

    def add_to_line(self, line):
        newline = []
        for entry in line:
            if entry[0] not in STUPIDAXES:
                newline.append(entry)
        self.datasaver.add_result(*newline)

    def write_line(self):
        pass

    def write_block(self):
        pass

