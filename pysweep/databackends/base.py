# The DataParameter class stores all information that belongs to a single data column
class DataParameter:
    def __init__(self, name, unit, paramtype='numeric', independent=False, extra_dependencies=None, duplicate=False):
        self.name = name  # name and label of this parameter
        self.unit = unit  # The unit belonging to values of this type
        self.paramtype = paramtype  # the type of the value
        self.independent = independent  # Is this a column a dependent or independent variable type,
        # 0 = False,
        # 1 = True,
        # 2 is Independent, but pysweep will not recognize it as such, meaning that it will only show up as an
        # independent for variables that add it as an independent via exta_dependencies
        if extra_dependencies is None:
            self.extra_dependencies = []
        else:
            self.extra_dependencies = extra_dependencies
        self.duplicate=duplicate

    def __repr__(self):
        r = [str(self.__class__), str(self.name), str(self.unit), str(self.paramtype), str(self.independent)]
        return " ".join(r)

class DataParameterFixedSweep(DataParameter):
    def __init__(self, name, unit, paramtype, start, stop, npoints):
        super().__init__(name, unit, paramtype, True)
        self.start = start
        self.stop = stop
        self.npoints = npoints

    def __repr__(self):
        r = [str(self.__class__), str(self.name), str(self.unit), str(self.paramtype), str(self.independent), str(self.npoints)]
        return " ".join(r)

# A databackend is responsible for storing the information that that is acquired by pysweep
# Since different situations could use different backends,
# this file defines the interface that pysweep will use to control the data backend
class DataBackend:
    def setup(self, paramstructure):
        # This function is called to signal that a measurement is coming
        # it contains the parameter structure which is a list of DataParameters
        # every DataParameter can in principle depend on all independents preceding it
        raise NotImplementedError()

    def __enter__(self):
        # This function will be called as soon as the pysweep sweeep enters the measurement context which happens immediately before the measurement starts
        # It should return an instance of DataSaver
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb):
        '''
        This function will be called after the measurement finishes (or crashes)
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        '''
        raise NotImplementedError()

# This class defines how
class DataSaver:
    # pysweep will dump line information here which will consists of a list of tuples with name, value to store
    def add_to_line(self, line):
        raise NotImplementedError()

    # This functions will be called to signal that all values that are added to the new mine are final
    # and can be written away
    def write_line(self):
        raise NotImplementedError()

    # This function will be called after every innermost loop
    def write_block(self):
        raise NotImplementedError()

class CombinedDataBackend(DataBackend, DataSaver):
    def __init__(self, databackends):
        self.databackends = databackends
        self.datasavers = None

    def setup(self, paramstructure):
        for db in self.databackends:
            db.setup(paramstructure)

    def __enter__(self):
        self.datasavers = []
        for db in self.databackends:
            self.datasavers.append(db.__enter__())

    def __exit__(self, exc_type, exc_val, exc_tb):
        for db in self.databackends:
            db.__exit__( exc_type, exc_val, exc_tb)

    def add_to_line(self, line):
        for db in self.databackends:
            db.add_to_line(line)

    def write_line(self):
        for db in self.databackends:
            db.write_line()

    def write_block(self):
        for db in self.databackends:
            db.write_block()





