from pysweep.core.measurementfunctions import MeasurementFunction
from pysweep.databackends.base import DataParameter, DataParameterFixedSweep

class SweepObject:
    def __init__(self, set_function, unit, label, point_function, dataparameter=None):
        '''

        :param set_function:
        :param unit:
        :param label:
        :param point_function:
        :param dataparameter: when this parameter is None (default), the point_function will be executed once to determine the dataparameter
        '''
        self.set_function = set_function
        self.unit = unit
        self.label = label
        self.point_function = point_function
        if dataparameter is None:
            points, _ = self.point_function({})
            self.dataparameter = DataParameterFixedSweep(self.label, self.unit, 'numeric', points[0], points[-1], len(points))
        elif isinstance(dataparameter, DataParameter):
            self.dataparameter = dataparameter
        else:
            # assume that dataparameter is some list that contains a mock version of the points we will be sweeping over
            self.dataparameter = DataParameterFixedSweep(self.label, self.unit, 'numeric', dataparameter[0], dataparameter[-1], len(dataparameter))
        if not isinstance(self.set_function, MeasurementFunction):
            raise TypeError('Set function '+repr(self.set_function)+ ' is not of type pysweep.core.measurementfunctions.MeasurementFunction')

        if not isinstance(self.point_function, MeasurementFunction):
            raise TypeError('Set function '+repr(self.set_function)+ ' is not of type pysweep.core.measurementfunctions.MeasurementFunction')

    def get_dataparameter(self) -> DataParameter:
        return self.dataparameter
