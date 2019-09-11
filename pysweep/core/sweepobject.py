from pysweep.core.measurementfunctions import MeasurementFunction

class SweepObject:
    def __init__(self, set_function, unit, label, point_function):
        self.set_function = set_function
        self.unit = unit
        self.label = label
        self.point_function = point_function
        if not isinstance(self.set_function, MeasurementFunction):
            raise TypeError('Set function '+repr(self.set_function)+ ' is not of type pysweep.core.measurementfunctions.MeasurementFunction')

        if not isinstance(self.point_function, MeasurementFunction):
            raise TypeError('Set function '+repr(self.set_function)+ ' is not of type pysweep.core.measurementfunctions.MeasurementFunction')
